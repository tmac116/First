import { useState } from 'react';

export function BudgetSetup({ categories, budgetLimits, onSetLimit }) {
  const [values, setValues] = useState(() => {
    const init = {};
    categories.forEach(c => { init[c] = budgetLimits[c] ?? ''; });
    return init;
  });

  function handleChange(cat, val) {
    setValues(prev => ({ ...prev, [cat]: val }));
  }

  function handleSave(cat) {
    const amount = parseFloat(values[cat]);
    if (!isNaN(amount) && amount > 0) {
      onSetLimit(cat, amount);
    }
  }

  function handleKeyDown(e, cat) {
    if (e.key === 'Enter') handleSave(cat);
  }

  const fmt = (n) => n ? n.toLocaleString('en-US', { style: 'currency', currency: 'USD' }) : null;

  return (
    <div className="budget-setup">
      <h2>Monthly Budget Limits</h2>
      <p className="section-desc">Set spending limits per category to track your budget progress.</p>
      <div className="budget-grid">
        {categories.map(cat => (
          <div key={cat} className="budget-row">
            <span className="budget-cat">{cat}</span>
            {budgetLimits[cat] ? (
              <span className="budget-current">{fmt(budgetLimits[cat])}/mo</span>
            ) : null}
            <div className="budget-input-group">
              <input
                type="number"
                value={values[cat]}
                onChange={e => handleChange(cat, e.target.value)}
                onKeyDown={e => handleKeyDown(e, cat)}
                placeholder="Limit"
                min="1"
                step="1"
              />
              <button className="btn-save" onClick={() => handleSave(cat)}>Set</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
