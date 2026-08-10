'use client';

import { useEffect, useRef, useState } from 'react';
import { fetchHazardAdvisory, hazardMeta, ONSET_LABELS } from '@/lib/hazards';
import { LANGUAGE_LABELS, ROLES } from '@/lib/constants';

/**
 * The expanded view of one hazard: measurements, recent events, and the
 * advisory that says what to do.
 *
 * The advisory is fetched when this panel opens rather than with the profile.
 * Generating nine advisories in every language for every page view would exhaust
 * the model quota in minutes and slow the profile down for everyone, and the
 * reader only ever wants prose for the card they actually opened.
 */
export default function HazardDetail({ risk, location, onClose }) {
  const [role, setRole] = useState('general');
  const [language, setLanguage] = useState('en');
  const [advisory, setAdvisory] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const requestId = useRef(0);
  const meta = hazardMeta(risk.hazard);
  const level = risk.risk_level.toLowerCase();

  useEffect(() => {
    const id = ++requestId.current;
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    setError(null);

    fetchHazardAdvisory(risk.hazard, location, { role, language, signal: controller.signal })
      .then((data) => {
        if (id === requestId.current) {
          setAdvisory(data.advisory);
          setError(null);
        }
      })
      .catch((e) => {
        if (id === requestId.current && e.name !== 'AbortError') {
          setError('The advisory could not be generated. The measurements below are still current.');
        }
      })
      .finally(() => {
        if (id === requestId.current) setLoading(false);
      });

    return () => controller.abort();
    // Depends on the coordinates rather than the `location` object: the parent
    // rebuilds that object on every render, so depending on its identity would
    // refetch the advisory in a loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [risk.hazard, location.latitude, location.longitude, role, language]);

  return (
    <div className="hazard-detail">
      <button className="mobile-back-btn" onClick={onClose}>
        ← Back to hazards
      </button>

      <header className="hazard-detail-head">
        <span className="hazard-detail-icon" aria-hidden="true">
          {meta.icon}
        </span>
        <div>
          <h2 className="hazard-detail-title">{meta.label}</h2>
          <div className="hazard-detail-sub">
            <span className={`risk-badge risk-badge--${level}`}>{risk.risk_level}</span>
            <span>{ONSET_LABELS[risk.onset] || risk.onset}</span>
          </div>
        </div>
      </header>

      <div className="card">
        <p className="hazard-detail-headline">{risk.headline}</p>
        {risk.summary && <p className="hazard-detail-summary">{risk.summary}</p>}

        {/* Warning time is stated on every card, including the ones where the
            honest answer is that there isn't any. A reader who assumes an
            earthquake card works like a forecast has been misled by omission. */}
        {risk.lead_time && (
          <p className="hazard-detail-lead">
            <span className="hazard-detail-lead-label">Warning time</span>
            {risk.lead_time}
          </p>
        )}
      </div>

      {risk.indicators.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">What this is based on</div>
          </div>
          <dl className="indicator-list">
            {risk.indicators.map((indicator) => (
              <div className="indicator" key={indicator.label}>
                <dt className="indicator-label">{indicator.label}</dt>
                <dd className="indicator-value">
                  {indicator.value}
                  {indicator.trend && (
                    <span className={`indicator-trend indicator-trend--${indicator.trend}`}>
                      {indicator.trend === 'rising' ? '↑' : indicator.trend === 'falling' ? '↓' : '→'}
                      {indicator.trend}
                    </span>
                  )}
                  {indicator.detail && (
                    <span className="indicator-detail">{indicator.detail}</span>
                  )}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {risk.events.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">Recent events</div>
          </div>
          <ul className="event-list">
            {risk.events.map((event) => (
              <li key={event.id} className="event-item">
                <div className="event-title">
                  {event.url ? (
                    <a href={event.url} target="_blank" rel="noopener noreferrer">
                      {event.title}
                    </a>
                  ) : (
                    event.title
                  )}
                </div>
                <div className="event-meta">
                  {event.distance_km != null && <span>{event.distance_km.toFixed(0)} km away</span>}
                  {event.depth_km != null && <span>{event.depth_km.toFixed(0)} km deep</span>}
                  {event.occurred_at && (
                    <span>{new Date(event.occurred_at).toLocaleString()}</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <div className="card-title">What to do</div>
          {loading && <span className="card-subtitle">Writing…</span>}
        </div>

        <div className="advisory-controls">
          <div className="form-group">
            <label className="form-label" htmlFor="hazard-role">
              Written for
            </label>
            <select
              id="hazard-role"
              className="form-select"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>

          {/* Only languages the backend says are actually spoken here. Offering
              Somali in Peru would be worse than useless — it would push the
              English version out of view. */}
          {location.languages && location.languages.length > 1 && (
            <div className="form-group">
              <label className="form-label">Language</label>
              <div className="lang-selector">
                {location.languages.map((code) => (
                  <button
                    key={code}
                    type="button"
                    className={`lang-btn ${language === code ? 'active' : ''}`}
                    onClick={() => setLanguage(code)}
                  >
                    {LANGUAGE_LABELS[code] || code}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="notice notice--error" role="alert">
            {error}
          </div>
        )}

        {loading && !advisory ? (
          <div className="loading-container">
            <div className="spinner" />
          </div>
        ) : advisory ? (
          <div className={`advisory-card advisory-card--${level}`}>
            <h3 className="advisory-title">{advisory.title}</h3>
            <p className="advisory-body">{advisory.body}</p>
            {advisory.actions.length > 0 && (
              <ul className="advisory-actions">
                {advisory.actions.map((action, i) => (
                  <li key={i}>{action}</li>
                ))}
              </ul>
            )}

            {/* When the model could not write the language that was asked for,
                say so. Handing someone English while implying it is their
                language is the worse failure of the two. */}
            {advisory.language !== advisory.requested_language && (
              <p className="advisory-fallback-note">
                This advisory could not be written reliably in{' '}
                {LANGUAGE_LABELS[advisory.requested_language] || advisory.requested_language}, so it
                is shown in {LANGUAGE_LABELS[advisory.language] || advisory.language} instead.
              </p>
            )}

            {advisory.ai_generated ? (
              <p className="advisory-ai-note">
                Written by AI from the measurements above. AI can make mistakes — the
                measurements and the official sources are the record.
              </p>
            ) : (
              <p className="advisory-ai-note">
                Standard safety guidance, written and reviewed by people. The AI writer was
                unavailable.
              </p>
            )}
          </div>
        ) : null}
      </div>

      <div className="card hazard-sources">
        <div className="card-header">
          <div className="card-title">Where this comes from</div>
        </div>
        <ul className="source-list">
          {risk.data_sources.map((source) => (
            <li key={source}>{source}</li>
          ))}
        </ul>
        {risk.note && <p className="source-note">{risk.note}</p>}
        <p className="source-confidence">
          Confidence in this assessment: {Math.round(risk.confidence * 100)}%
        </p>
      </div>
    </div>
  );
}
