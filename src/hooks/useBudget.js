import { useState, useEffect } from 'react';

const STORAGE_KEY = 'budget_app_data';

const DEFAULT_CATEGORIES = [
  'Housing', 'Food', 'Transport', 'Entertainment', 'Health', 'Shopping', 'Utilities', 'Other'
];

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveToStorage(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

export function useBudget() {
  const [transactions, setTransactions] = useState(() => {
    const saved = loadFromStorage();
    return saved?.transactions ?? [];
  });

  const [budgetLimits, setBudgetLimits] = useState(() => {
    const saved = loadFromStorage();
    return saved?.budgetLimits ?? {};
  });

  const categories = DEFAULT_CATEGORIES;

  useEffect(() => {
    saveToStorage({ transactions, budgetLimits });
  }, [transactions, budgetLimits]);

  function addTransaction(transaction) {
    setTransactions(prev => [
      { ...transaction, id: Date.now().toString() },
      ...prev,
    ]);
  }

  function deleteTransaction(id) {
    setTransactions(prev => prev.filter(t => t.id !== id));
  }

  function setBudgetLimit(category, amount) {
    setBudgetLimits(prev => ({ ...prev, [category]: parseFloat(amount) }));
  }

  const totalIncome = transactions
    .filter(t => t.type === 'income')
    .reduce((sum, t) => sum + t.amount, 0);

  const totalExpenses = transactions
    .filter(t => t.type === 'expense')
    .reduce((sum, t) => sum + t.amount, 0);

  const balance = totalIncome - totalExpenses;

  const expensesByCategory = categories.reduce((acc, cat) => {
    acc[cat] = transactions
      .filter(t => t.type === 'expense' && t.category === cat)
      .reduce((sum, t) => sum + t.amount, 0);
    return acc;
  }, {});

  return {
    transactions,
    budgetLimits,
    categories,
    totalIncome,
    totalExpenses,
    balance,
    expensesByCategory,
    addTransaction,
    deleteTransaction,
    setBudgetLimit,
  };
}
