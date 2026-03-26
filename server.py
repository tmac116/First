#!/usr/bin/env python3
"""
Meeting Notes web server.

Serves the frontend and exposes POST /api/process which:
  1. Accepts an audio upload (any format — ffmpeg handles it)
  2. Transcribes with faster-whisper
  3. Streams structured meeting notes from Claude as Server-Sent Events

Set ANTHROPIC_API_KEY in the environment before starting.
Optional: WHISPER_MODEL=tiny|base|small|medium|large  (default: base)
"""

import os
import json
import asyncio
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

import numpy as np
from faster_whisper import WhisperModel
import anthropic
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# ── Globals ──────────────────────────────────────────────────────────────────

_whisper: WhisperModel | None = None
_anthropic = anthropic.Anthropic()

SYSTEM_PROMPT = (
    "You are an expert meeting note-taker. "
    "Transform raw transcripts into concise, professional meeting notes. "
    "Be accurate — only include what was actually discussed."
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _whisper
    model_name = os.getenv("WHISPER_MODEL", "base")
    print(f"Loading Whisper '{model_name}' model…", flush=True)
    _whisper = await asyncio.to_thread(
        WhisperModel, model_name, device="cpu", compute_type="int8"
    )
    print("Whisper ready.", flush=True)
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/process")
async def process_audio(audio: UploadFile = File(...)):
    """Accept an audio upload and stream SSE: status → transcript → notes chunks → done."""
    if _whisper is None:
        raise HTTPException(503, "Model not ready yet — please retry in a moment.")
    return StreamingResponse(
        _event_stream(audio),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # prevent nginx/Fly.io proxy buffering
        },
    )


# ── Core pipeline ─────────────────────────────────────────────────────────────

def _sse(event_type: str, **kwargs) -> str:
    """Format a single SSE frame."""
    payload = json.dumps({"type": event_type, **kwargs})
    return f"data: {payload}\n\n"


async def _event_stream(audio: UploadFile):
    """Async generator that drives the full pipeline and yields SSE frames."""
    # Choose file extension from MIME type so ffmpeg gets the right decoder hint
    mime = (audio.content_type or "").lower()
    if "mp4" in mime or "m4a" in mime:
        suffix = ".m4a"
    elif "ogg" in mime:
        suffix = ".ogg"
    elif "webm" in mime:
        suffix = ".webm"
    else:
        suffix = Path(audio.filename or "audio").suffix or ".audio"

    tmp_path: str | None = None
    try:
        content = await audio.read()
        size_kb = len(content) // 1024
        yield _sse("status", message=f"Received {size_kb} KB · transcribing…")

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # Decode + transcribe (blocking — run in thread pool)
        audio_array = await asyncio.to_thread(_decode_audio, tmp_path)

        if len(audio_array) < 16_000:  # less than 1 second of audio
            yield _sse("error", message="Recording too short. Please speak for at least a second.")
            return

        transcript = await asyncio.to_thread(_transcribe, audio_array)

        if not transcript:
            yield _sse("error", message="No speech detected. Try speaking louder or closer to the mic.")
            return

        yield _sse("transcript", text=transcript)
        yield _sse("status", message="Transcription done · generating notes…")

        # Stream Claude notes
        notes_prompt = _build_prompt(transcript)
        with _anthropic.messages.stream(
            model="claude-opus-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": notes_prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield _sse("chunk", text=text)

        yield _sse("done")

    except Exception as exc:
        yield _sse("error", message=str(exc))
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


def _decode_audio(path: str) -> np.ndarray:
    """Use ffmpeg to decode any audio format to 16 kHz mono float32 PCM."""
    cmd = [
        "ffmpeg", "-nostdin", "-threads", "0",
        "-i", path,
        "-f", "f32le", "-ac", "1", "-ar", "16000",
        "pipe:1",
    ]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Audio decode failed: {proc.stderr.decode(errors='replace')[:300]}"
        )
    return np.frombuffer(proc.stdout, dtype=np.float32)


def _transcribe(audio: np.ndarray) -> str:
    """Run faster-whisper and return the full transcript as a single string."""
    segments, _ = _whisper.transcribe(audio, beam_size=5, vad_filter=True)
    return " ".join(s.text.strip() for s in segments).strip()


def _build_prompt(transcript: str) -> str:
    today = datetime.now().strftime("%B %d, %Y")
    return f"""Create structured meeting notes from the transcript below.

Use this format (omit any section with no relevant content):

# Meeting Notes
**Date:** {today}

## Summary
[2–3 sentence overview]

## Key Discussion Points
- [bullet points]

## Decisions Made
- [decisions reached]

## Action Items
- [tasks, with owner if mentioned]

## Next Steps
- [follow-ups or open questions]

---

**Transcript:**
{transcript}"""
