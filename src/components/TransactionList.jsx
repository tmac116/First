export function TransactionList({ transactions, onDelete }) {
  const fmt = (n) => n.toLocaleString('en-US', { style: 'currency', currency: 'USD' });

  if (transactions.length === 0) {
    return (
      <div className="transaction-list">
        <h2>Transactions</h2>
        <p className="empty-state">No transactions yet. Add your first one above!</p>
      </div>
    );
  }

  return (
    <div className="transaction-list">
      <h2>Transactions</h2>
      <ul>
        {transactions.map(t => (
          <li key={t.id} className={`transaction-item ${t.type}`}>
            <div className="transaction-info">
              <span className="transaction-desc">{t.description}</span>
              <span className="transaction-meta">{t.category} &middot; {t.date}</span>
            </div>
            <div className="transaction-right">
              <span className={`transaction-amount ${t.type === 'income' ? 'positive' : 'negative'}`}>
                {t.type === 'income' ? '+' : '-'}{fmt(t.amount)}
              </span>
              <button className="btn-delete" onClick={() => onDelete(t.id)} title="Delete">×</button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
