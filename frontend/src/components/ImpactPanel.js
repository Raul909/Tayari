'use client';

export default function ImpactPanel({ impact }) {
  if (!impact) return null;

  return (
    <div>
      <div className="impact-grid">
        <div className="impact-item">
          <div className="impact-value">
            {impact.estimated_population_at_risk
              ? `~${impact.estimated_population_at_risk.toLocaleString()}`
              : '0'}
          </div>
          <div className="impact-label">Est. people at risk</div>
        </div>
        <div className="impact-item">
          <div className="impact-value">{impact.schools_at_risk || 0}</div>
          <div className="impact-label">Schools</div>
        </div>
        <div className="impact-item">
          <div className="impact-value">
            {(impact.clinics_at_risk || 0) + (impact.hospitals_at_risk || 0)}
          </div>
          <div className="impact-label">Health Facilities</div>
        </div>
        <div className="impact-item">
          <div className="impact-value">{impact.markets_at_risk || 0}</div>
          <div className="impact-label">Markets</div>
        </div>
      </div>

      {impact.flood_zone_km > 0 && (
        <div
          style={{
            marginTop: '12px',
            fontSize: '12px',
            color: 'var(--text-muted)',
            textAlign: 'center',
          }}
        >
          Projected flood zone: {impact.flood_zone_km} km from river
        </div>
      )}

      <div
        style={{
          marginTop: '8px',
          fontSize: '11px',
          color: 'var(--text-muted)',
          textAlign: 'center',
          fontStyle: 'italic',
        }}
      >
        Estimates from OCHA/IOM displacement data &amp; infrastructure mapping — not a live headcount.
      </div>
    </div>
  );
}
