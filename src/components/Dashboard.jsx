export function Dashboard({ totalIncome, totalExpenses, balance, expensesByCategory, budgetLimits, categories }) {
  const fmt = (n) => n.toLocaleString('en-US', { style: 'currency', currency: 'USD' });

  return (
    <div className="dashboard">
      <div className="summary-cards">
        <div className="card card-balance">
          <span className="card-label">Balance</span>
          <span className={`card-value ${balance >= 0 ? 'positive' : 'negative'}`}>{fmt(balance)}</span>
        </div>
        <div className="card card-income">
          <span className="card-label">Total Income</span>
          <span className="card-value positive">{fmt(totalIncome)}</span>
        </div>
        <div className="card card-expense">
          <span className="card-label">Total Expenses</span>
          <span className="card-value negative">{fmt(totalExpenses)}</span>
        </div>
      </div>

      <div className="category-breakdown">
        <h2>Spending by Category</h2>
        {categories.map(cat => {
          const spent = expensesByCategory[cat] || 0;
          const limit = budgetLimits[cat];
          const pct = limit ? Math.min((spent / limit) * 100, 100) : null;
          const overBudget = limit && spent > limit;

          if (spent === 0 && !limit) return null;

          return (
            <div key={cat} className="category-row">
              <div className="category-header">
                <span className="category-name">{cat}</span>
                <span className="category-amounts">
                  <span className={overBudget ? 'negative' : ''}>{fmt(spent)}</span>
                  {limit ? <span className="limit-text"> / {fmt(limit)}</span> : null}
                </span>
              </div>
              {limit ? (
                <div className="progress-bar-bg">
                  <div
                    className={`progress-bar-fill ${overBudget ? 'over-budget' : ''}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              ) : null}
            </div>
          );
        })}
        {categories.every(cat => !expensesByCategory[cat] && !budgetLimits[cat]) && (
          <p className="empty-state">No spending data yet. Add transactions to see your breakdown.</p>
        )}
      </div>
    </div>
  );
}
