import { useState } from 'react';

export function TransactionForm({ categories, onAdd }) {
  const today = new Date().toISOString().split('T')[0];
  const [form, setForm] = useState({
    type: 'expense',
    description: '',
    amount: '',
    category: categories[0],
    date: today,
  });

  function handleChange(e) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    const amount = parseFloat(form.amount);
    if (!form.description.trim() || isNaN(amount) || amount <= 0) return;

    onAdd({
      type: form.type,
      description: form.description.trim(),
      amount,
      category: form.type === 'income' ? 'Income' : form.category,
      date: form.date,
    });

    setForm(prev => ({ ...prev, description: '', amount: '' }));
  }

  return (
    <form className="transaction-form" onSubmit={handleSubmit}>
      <h2>Add Transaction</h2>

      <div className="form-row">
        <label className="radio-option">
          <input type="radio" name="type" value="expense" checked={form.type === 'expense'} onChange={handleChange} />
          Expense
        </label>
        <label className="radio-option">
          <input type="radio" name="type" value="income" checked={form.type === 'income'} onChange={handleChange} />
          Income
        </label>
      </div>

      <div className="form-grid">
        <div className="form-group">
          <label>Description</label>
          <input
            type="text"
            name="description"
            value={form.description}
            onChange={handleChange}
            placeholder="e.g. Grocery run"
            required
          />
        </div>

        <div className="form-group">
          <label>Amount ($)</label>
          <input
            type="number"
            name="amount"
            value={form.amount}
            onChange={handleChange}
            placeholder="0.00"
            min="0.01"
            step="0.01"
            required
          />
        </div>

        {form.type === 'expense' && (
          <div className="form-group">
            <label>Category</label>
            <select name="category" value={form.category} onChange={handleChange}>
              {categories.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        )}

        <div className="form-group">
          <label>Date</label>
          <input
            type="date"
            name="date"
            value={form.date}
            onChange={handleChange}
            required
          />
        </div>
      </div>

      <button type="submit" className="btn-primary">Add Transaction</button>
    </form>
  );
}
