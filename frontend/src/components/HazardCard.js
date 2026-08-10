'use client';

import { hazardMeta, ONSET_LABELS } from '@/lib/hazards';

/**
 * One hazard, as a row in the location's list.
 *
 * The design decision that matters here is what leads. Not the score — a number
 * between 0 and 1 tells a reader nothing on its own — but the headline sentence
 * the assessor wrote, which already says what is happening in plain words. The
 * risk badge and the onset sit alongside it as qualifiers, because knowing
 * whether you have five minutes or five weeks changes the response as much as
 * knowing how bad it is.
 */
export default function HazardCard({ risk, active, onSelect }) {
  const meta = hazardMeta(risk.hazard);
  const level = risk.risk_level.toLowerCase();

  return (
    <button
      type="button"
      className={`hazard-card ${active ? 'active' : ''}`}
      onClick={() => onSelect(risk)}
      aria-pressed={active}
    >
      <span className="hazard-card-icon" aria-hidden="true">
        {meta.icon}
      </span>

      <span className="hazard-card-body">
        <span className="hazard-card-top">
          <span className="hazard-card-label">{meta.label}</span>
          <span className={`risk-badge risk-badge--${level}`}>{risk.risk_level}</span>
        </span>

        <span className="hazard-card-headline">{risk.headline}</span>

        <span className="hazard-card-meta">
          <span>{ONSET_LABELS[risk.onset] || risk.onset}</span>
          {/* Susceptibility only earns space when it is the more interesting
              number — i.e. when a place is badly exposed to something that is
              not currently happening. That is exactly the case a reader is
              most likely to misread as "nothing to worry about". */}
          {risk.risk_level === 'LOW' && risk.susceptibility >= 0.5 && (
            <>
              <span aria-hidden="true">·</span>
              <span>Exposed area, quiet right now</span>
            </>
          )}
          {risk.degraded && (
            <>
              <span aria-hidden="true">·</span>
              <span className="hazard-card-degraded">Partial data</span>
            </>
          )}
        </span>
      </span>
    </button>
  );
}
