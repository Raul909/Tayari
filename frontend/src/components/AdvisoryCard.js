'use client';

export default function AdvisoryCard({ advisory }) {
  if (!advisory) return null;

  const level = advisory.risk_level?.toLowerCase() || 'low';

  return (
    <div className={`advisory-card advisory-card--${level}`}>
      <div className="advisory-title">{advisory.title}</div>
      <div className="advisory-body">{advisory.body}</div>
      {advisory.actions && advisory.actions.length > 0 && (
        <ul className="advisory-actions">
          {advisory.actions.map((action, i) => (
            <li key={i}>{action}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
