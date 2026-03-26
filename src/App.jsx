import { useState } from 'react';
import { useBudget } from './hooks/useBudget';
import { Dashboard } from './components/Dashboard';
import { TransactionForm } from './components/TransactionForm';
import { TransactionList } from './components/TransactionList';
import { BudgetSetup } from './components/BudgetSetup';
import './App.css';

const TABS = ['Dashboard', 'Transactions', 'Budget'];

export default function App() {
  const [activeTab, setActiveTab] = useState('Dashboard');
  const budget = useBudget();

  return (
    <div className="app">
      <header className="app-header">
        <h1>My Budget</h1>
        <nav className="tab-nav">
          {TABS.map(tab => (
            <button
              key={tab}
              className={`tab-btn ${activeTab === tab ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
            </button>
          ))}
        </nav>
      </header>

      <main className="app-main">
        {activeTab === 'Dashboard' && (
          <Dashboard
            totalIncome={budget.totalIncome}
            totalExpenses={budget.totalExpenses}
            balance={budget.balance}
            expensesByCategory={budget.expensesByCategory}
            budgetLimits={budget.budgetLimits}
            categories={budget.categories}
          />
        )}
        {activeTab === 'Transactions' && (
          <>
            <TransactionForm categories={budget.categories} onAdd={budget.addTransaction} />
            <TransactionList transactions={budget.transactions} onDelete={budget.deleteTransaction} />
          </>
        )}
        {activeTab === 'Budget' && (
          <BudgetSetup
            categories={budget.categories}
            budgetLimits={budget.budgetLimits}
            onSetLimit={budget.setBudgetLimit}
          />
        )}
      </main>
    </div>
  );
}
