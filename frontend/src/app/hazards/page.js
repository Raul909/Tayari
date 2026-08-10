'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { fetchHazardTypes, fetchLiveEvents, hazardMeta, ONSET_LABELS } from '@/lib/hazards';
import { BASINS } from '@/lib/constants';

/**
 * The hazard guide: what Tayari watches, and what to do about each one.
 *
 * This replaces "Basins" in the navigation. A river basin is a flood-only
 * concept and a piece of hydrology jargon, and having it as a top-level
 * destination in a nine-hazard product told the wrong story about what the app
 * is — someone worried about earthquakes had no obvious way in.
 *
 * The eight calibrated basins are not gone; they have moved to where they
 * belong, as a detail of the flood hazard, because that is what they are.
 */
export default function HazardsPage() {
  const [hazards, setHazards] = useState([]);
  const [selected, setSelected] = useState(null);
  const [events, setEvents] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetchHazardTypes()
      .then((data) => {
        if (cancelled) return;
        setHazards(data.hazards || []);
        // Deep link support: /hazards?h=volcano opens that hazard directly, so
        // the dashboard and the alert form can point at a specific card.
        const wanted = new URLSearchParams(window.location.search).get('h');
        const match = (data.hazards || []).find((x) => x.hazard === wanted);
        if (match) setSelected(match);
      })
      .catch(() => {
        if (!cancelled) setError('Could not load the hazard list. Please try again in a moment.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    fetchLiveEvents({ minMagnitude: 4.5, days: 7 })
      .then((data) => !cancelled && setEvents(data))
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Hazards</h1>
        <p className="page-description">
          The nine hazards Tayari watches, what warning each one gives you, and where its
          numbers come from. Pick one to see what is happening now and to set up an alert.
        </p>
      </div>

      {error && (
        <div className="notice notice--error" role="alert">
          {error}
        </div>
      )}

      {loading ? (
        <div className="loading-container">
          <div className="spinner" />
        </div>
      ) : (
        <div className="hazard-guide">
          <div className="hazard-grid">
            {hazards.map((h) => {
              const meta = hazardMeta(h.hazard);
              const active = selected?.hazard === h.hazard;
              return (
                <button
                  key={h.hazard}
                  type="button"
                  className={`hazard-tile ${active ? 'active' : ''}`}
                  onClick={() => setSelected(active ? null : h)}
                  aria-pressed={active}
                >
                  <span className="hazard-tile-icon" aria-hidden="true">
                    {meta.icon}
                  </span>
                  <span className="hazard-tile-label">{h.label}</span>
                  <span className="hazard-tile-onset">
                    {h.forecastable ? ONSET_LABELS[h.onset] || h.onset : 'No forecast possible'}
                  </span>
                </button>
              );
            })}
          </div>

          {selected ? (
            <HazardDetailPanel hazard={selected} events={events} />
          ) : (
            <div className="card hazard-guide-empty">
              <p>
                Select a hazard above to read what it is, how much warning it gives, where the
                data comes from, and to send an advisory to a phone.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function HazardDetailPanel({ hazard, events }) {
  const meta = hazardMeta(hazard.hazard);

  // Live counts, but only for the two hazards where "happening right now
  // somewhere on Earth" is a meaningful global statement. A heatwave is
  // intensely local; there is no honest worldwide count of one.
  const liveCount =
    hazard.hazard === 'earthquake'
      ? events?.earthquakes?.length
      : hazard.hazard === 'volcano'
        ? events?.volcanoes?.length
        : null;
  const liveUnavailable =
    hazard.hazard === 'volcano' && events?.unavailable?.includes('volcanoes');

  return (
    <div className="hazard-guide-detail">
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <span aria-hidden="true" style={{ marginRight: 8 }}>
              {meta.icon}
            </span>
            {hazard.label}
          </div>
        </div>

        <p className="hazard-guide-desc">{hazard.description}</p>

        <dl className="hazard-facts">
          <div>
            <dt>Warning time</dt>
            <dd>{hazard.lead_time}</dd>
          </div>
          <div>
            <dt>How fast it arrives</dt>
            <dd>{ONSET_LABELS[hazard.onset] || hazard.onset}</dd>
          </div>
          <div>
            <dt>Can it be forecast?</dt>
            <dd>
              {hazard.forecastable
                ? 'Yes — this card is a forecast'
                : 'No — this card is about readiness and what has already happened'}
            </dd>
          </div>
        </dl>

        {liveCount != null && !liveUnavailable && (
          <p className="hazard-live">
            <strong>{liveCount}</strong>{' '}
            {hazard.hazard === 'earthquake'
              ? 'earthquakes of magnitude 4.5 or above worldwide in the last 7 days'
              : 'volcanoes currently erupting worldwide'}
          </p>
        )}
        {liveUnavailable && (
          <p className="hazard-live hazard-live--degraded">
            The eruption feed could not be reached, so no live count is shown rather than a
            zero that would read as &ldquo;nothing is erupting&rdquo;.
          </p>
        )}

        <div className="hazard-guide-actions">
          <Link href="/" className="btn btn-primary">
            Check this at my location
          </Link>
          <Link href={`/alerts?hazard=${hazard.hazard}`} className="btn">
            Set up an alert
          </Link>
        </div>
      </div>

      {/* The eight calibrated basins live under flood, where they belong. */}
      {hazard.hazard === 'flood' && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">Eight individually calibrated rivers</div>
          </div>
          <p className="hazard-guide-desc">
            Anywhere else, Tayari estimates the flood threshold from the river&apos;s own
            five-year record. On these eight it is calibrated against documented historical
            floods and scored for skill, which makes them the more reliable answer.
          </p>
          <ul className="basin-mini-list">
            {Object.values(BASINS).map((b) => (
              <li key={b.id}>
                <span className="basin-mini-name">{b.name}</span>
                <span className="basin-mini-meta">
                  {b.river} · {b.country}
                </span>
              </li>
            ))}
          </ul>
          <Link href="/basins" className="btn" style={{ marginTop: 12 }}>
            Open the basin dashboard
          </Link>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <div className="card-title">Where the numbers come from</div>
        </div>
        <ul className="source-list">
          {hazard.data_sources.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
