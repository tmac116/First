#!/usr/bin/env python3
"""
Meeting Notes - Record your meeting and get AI-powered structured notes.

Usage:
    python meeting_notes.py [--model MODEL]

Options:
    --model MODEL    Whisper model size: tiny, base, small, medium, large (default: base)

Requires ANTHROPIC_API_KEY environment variable.
"""

import os
import sys
import time
import argparse
import threading
import signal
import numpy as np
import sounddevice as sd
from datetime import datetime
from pathlib import Path

import whisper
import anthropic
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text
from rich import box

# ── Audio settings ────────────────────────────────────────────────────────────
SAMPLE_RATE = 16000   # Hz — Whisper works best at 16kHz
CHANNELS = 1          # Mono
DTYPE = "float32"

# Transcribe in 30-second windows after recording stops
CHUNK_SECONDS = 30

console = Console()


# ── Recording ─────────────────────────────────────────────────────────────────

class AudioRecorder:
    """Thread-safe audio recorder using sounddevice."""

    def __init__(self):
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None
        self.recording = False

    def _callback(self, indata: np.ndarray, frames: int, time_info, status):
        if status:
            console.print(f"[yellow]⚠ Audio: {status}[/yellow]")
        if self.recording:
            with self._lock:
                self._frames.append(indata.copy())

    def start(self):
        self._frames = []
        self.recording = True
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        """Stop recording and return all captured audio as a 1-D float32 array."""
        self.recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
        with self._lock:
            if self._frames:
                return np.concatenate(self._frames, axis=0).flatten()
        return np.array([], dtype=np.float32)


# ── Transcription ──────────────────────────────────────────────────────────────

def transcribe_audio(audio: np.ndarray, model, verbose: bool = True) -> list[str]:
    """
    Split audio into 30-second chunks and transcribe each one.
    Returns a list of text segments.
    """
    if len(audio) < SAMPLE_RATE:
        return []

    chunk_size = SAMPLE_RATE * CHUNK_SECONDS
    total_chunks = (len(audio) + chunk_size - 1) // chunk_size
    segments: list[str] = []

    for i, start in enumerate(range(0, len(audio), chunk_size)):
        chunk = audio[start : start + chunk_size]
        if len(chunk) < SAMPLE_RATE // 2:   # skip tiny trailing chunks
            continue
        if verbose:
            console.print(
                f"  [dim]Transcribing chunk {i + 1}/{total_chunks}…[/dim]"
            )
        result = model.transcribe(chunk, fp16=False, language=None)
        text = result["text"].strip()
        if text:
            segments.append(text)

    return segments


# ── Note generation ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are an expert meeting note-taker. "
    "Transform raw transcripts into concise, professional meeting notes. "
    "Be accurate — only include what was actually discussed."
)

def generate_notes(transcript: str, client: anthropic.Anthropic) -> str:
    """Stream meeting notes from Claude based on the full transcript."""

    user_message = f"""Create structured meeting notes from the transcript below.

Use this format (omit any section that has no relevant content):

# Meeting Notes
**Date:** {datetime.now().strftime("%B %d, %Y")}

## Summary
[2–3 sentence overview]

## Key Discussion Points
[Bullet list of main topics covered]

## Decisions Made
[Decisions or conclusions reached]

## Action Items
[Tasks or commitments, with owner if mentioned]

## Next Steps
[Planned follow-ups or open questions]

---

**Transcript:**
{transcript}
"""

    notes = ""
    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            console.print(text, end="")
            notes += text

    return notes


# ── Persistence ────────────────────────────────────────────────────────────────

def save_notes(notes: str, transcript: str) -> Path:
    """Write the notes + raw transcript to a Markdown file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(f"meeting_notes_{timestamp}.md")
    with path.open("w", encoding="utf-8") as f:
        f.write(notes)
        f.write("\n\n---\n\n## Raw Transcript\n\n")
        f.write(transcript)
        f.write("\n")
    return path


# ── UI helpers ─────────────────────────────────────────────────────────────────

def recording_indicator(recorder: AudioRecorder):
    """Live display shown while recording."""
    start = time.time()
    with Live(refresh_per_second=4, console=console) as live:
        while recorder.recording:
            elapsed = time.time() - start
            mins, secs = divmod(int(elapsed), 60)
            live.update(
                Panel(
                    f"[bold red]● REC[/bold red]  "
                    f"[dim]{mins:02d}:{secs:02d}[/dim]\n\n"
                    "Speak clearly into your microphone.\n"
                    "[dim]Press [bold]ENTER[/bold] to stop.[/dim]",
                    title="Recording",
                    border_style="red",
                )
            )
            time.sleep(0.25)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AI-powered meeting notes")
    parser.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base)",
    )
    args = parser.parse_args()

    # Verify API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print(
            "[bold red]Error:[/bold red] ANTHROPIC_API_KEY is not set.\n"
            "Export it with: [dim]export ANTHROPIC_API_KEY=your-key[/dim]"
        )
        sys.exit(1)

    console.print(
        Panel.fit(
            "[bold blue]Meeting Notes[/bold blue]\n"
            "[dim]Whisper transcription · Claude Opus notes[/dim]",
            border_style="blue",
        )
    )

    # Load Whisper model
    with Live(
        Spinner("dots", text=f" Loading Whisper ({args.model}) model…"),
        refresh_per_second=10,
        console=console,
    ):
        whisper_model = whisper.load_model(args.model)
    console.print(f"[green]✓ Whisper ({args.model}) ready[/green]")

    anthropic_client = anthropic.Anthropic()

    # ── Recording phase ──────────────────────────────────────────────────────
    console.print("\nPress [bold]ENTER[/bold] to start recording…")
    input()

    recorder = AudioRecorder()
    recorder.start()

    # Show recording indicator in a background thread; main thread waits for Enter
    indicator_thread = threading.Thread(
        target=recording_indicator, args=(recorder,), daemon=True
    )
    indicator_thread.start()

    try:
        input()   # Block until the user presses Enter (or Ctrl-C)
    except KeyboardInterrupt:
        pass

    audio = recorder.stop()
    indicator_thread.join(timeout=1)

    duration = len(audio) / SAMPLE_RATE
    console.print(f"\n[green]✓ Recording stopped[/green] — {duration:.1f}s captured")

    if duration < 1.0:
        console.print("[yellow]Recording too short (< 1 s). Nothing to process.[/yellow]")
        sys.exit(0)

    # ── Transcription phase ──────────────────────────────────────────────────
    console.print("\n[bold]Transcribing…[/bold]")
    segments = transcribe_audio(audio, whisper_model)

    if not segments:
        console.print("[yellow]No speech detected. Nothing to process.[/yellow]")
        sys.exit(0)

    full_transcript = " ".join(segments)
    console.print(
        f"[green]✓ Transcription complete[/green] — "
        f"{len(segments)} segment(s), {len(full_transcript.split())} words"
    )

    # ── Note generation phase ────────────────────────────────────────────────
    console.print("\n[bold]Generating meeting notes…[/bold]\n")
    notes = generate_notes(full_transcript, anthropic_client)

    # ── Save ─────────────────────────────────────────────────────────────────
    output_path = save_notes(notes, full_transcript)
    console.print(
        f"\n\n[bold green]✓ Notes saved →[/bold green] [underline]{output_path}[/underline]"
    )


if __name__ == "__main__":
    main()
