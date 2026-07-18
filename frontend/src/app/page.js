'use client';

import { useRef, useEffect, useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import 'maplibre-gl/dist/maplibre-gl.css';
import { fetchBasins, fetchForecast, fetchAdvisory, fetchReports, resolveAssetUrl } from '@/lib/api';
import {
  RISK_COLORS,
  MAP_CENTER,
  MAP_STYLE_URL,
  ROLES,
  LANGUAGE_LABELS,
  REPORT_STATUSES,
} from '@/lib/constants';
import { getDeviceTier, mapOptionsForTier, loadMapLibrary, onIdle, TIERS } from '@/lib/perf';
import { useToast } from '@/components/Toast';
import RiskGauge from '@/components/RiskGauge';
import AdvisoryCard from '@/components/AdvisoryCard';
import ImpactPanel from '@/components/ImpactPanel';
import OnboardingSplash from '@/components/OnboardingSplash';
import { useAuth } from '@/lib/auth';

// chart.js (~150 KB) only appears once a basin is selected, so split it out of
// the initial dashboard bundle instead of shipping it to every first paint.
const ForecastChart = dynamic(() => import('@/components/ForecastChart'), {
  ssr: false,
  loading: () => (
    <div className="loading-container" style={{ padding: '24px' }}>
      <div className="spinner" />
    </div>
  ),
});

export default function Dashboard() {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  // The lazily-imported maplibre-gl namespace, kept so the marker effects can
  // construct Markers/Popups without importing the (heavy) module themselves.
  const maplibreRef = useRef(null);
  const markersRef = useRef([]);
  const reportMarkersRef = useRef([]);
  const resizeObserverRef = useRef(null);
  // Monotonic token so a slow forecast response can't overwrite a newer one.
  const forecastReqId = useRef(0);
  // Guards so the (async) map init runs exactly once even if several triggers fire.
  const mapInitStartedRef = useRef(false);
  const mapTierRef = useRef(TIERS.HIGH);

  const [basins, setBasins] = useState([]);
  const [reports, setReports] = useState([]);
  const [selectedBasin, setSelectedBasin] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(true);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [role, setRole] = useState('general');
  const [language, setLanguage] = useState('en');
  const [error, setError] = useState(null);
  // Map lifecycle: `mapReady` flips true once the style has loaded (markers wait
  // for it); `deferMap` means we're on a metered/low device and are waiting for
  // the user to tap "Load map" before pulling the bundle.
  const [mapReady, setMapReady] = useState(false);
  const [deferMap, setDeferMap] = useState(false);

  const { user, loading: authLoading, isGuest, setGuest } = useAuth();

  // Refs mirror role/language so map markers (created once) always read the
  // current values instead of a value captured when the marker was made.
  const roleRef = useRef(role);
  const languageRef = useRef(language);
  useEffect(() => {
    roleRef.current = role;
    languageRef.current = language;
  }, [role, language]);

  const { notify } = useToast();

  async function loadBasins() {
    try {
      setLoading(true);
      const data = await fetchBasins();
      setBasins(data);
      setError(null);
    } catch (err) {
      console.error('Failed to load basins:', err);
      const msg = 'Could not reach the Tayari API. Please check your connection or try again in a moment.';
      setError(msg);
      notify({ type: 'error', title: 'Connection failed', message: msg });
    } finally {
      setLoading(false);
    }
  }

  async function loadReports() {
    try {
      const data = await fetchReports();
      setReports(data);
    } catch (err) {
      // Non-fatal — the map still works without community reports.
      console.error('Failed to load reports:', err);
    }
  }

  const loadForecast = async (basin) => {
    const reqId = ++forecastReqId.current;
    setForecastLoading(true);
    try {
      const data = await fetchForecast(basin.id, roleRef.current, languageRef.current);
      if (reqId === forecastReqId.current) {
        setForecast(data);
      }
      // Some backend builds don't embed the advisory in the forecast payload.
      // When it's missing, pull it from the dedicated advisory endpoint and
      // patch it in, so the advisory card always renders. Still gated by reqId
      // so a stale basin's advisory can't overwrite a newer selection.
      if (!data.advisory) {
        try {
          const adv = await fetchAdvisory(
            basin.id,
            roleRef.current,
            languageRef.current
          );
          if (reqId === forecastReqId.current && adv?.advisory) {
            setForecast((prev) =>
              prev && prev.basin?.id === basin.id
                ? { ...prev, advisory: adv.advisory }
                : prev
            );
          }
        } catch (advErr) {
          // Non-fatal — the rest of the forecast still shows.
          console.error('Failed to load advisory fallback:', advErr);
        }
      }
    } catch (err) {
      console.error('Failed to load forecast:', err);
      if (reqId === forecastReqId.current) {
        notify({
          type: 'error',
          title: 'Forecast unavailable',
          message: `Could not load the forecast for ${basin.name}.`,
        });
      }
    } finally {
      if (reqId === forecastReqId.current) {
        setForecastLoading(false);
      }
    }
  };

  const selectBasin = (basin) => {
    setSelectedBasin(basin);
    if (mapInstance.current) {
      mapInstance.current.flyTo({
        center: [basin.longitude, basin.latitude],
        zoom: 9,
        duration: 1400,
        essential: true,
      });
    }
    const langs = basin.languages?.length ? basin.languages : ['en'];
    if (!langs.includes(languageRef.current)) {
      setLanguage(langs[0]);
    } else {
      loadForecast(basin);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadBasins();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadReports();
  }, []);

  // Create the map. Async because the maplibre bundle is code-split and pulled
  // on demand (keeping it off the initial dashboard load). Safe to call from
  // multiple triggers — the ref guard makes it idempotent.
  const initMap = useCallback(async () => {
    if (mapInitStartedRef.current || mapInstance.current || !mapRef.current) return;
    mapInitStartedRef.current = true;
    setDeferMap(false);

    try {
      const maplibregl = await loadMapLibrary();
      maplibreRef.current = maplibregl;
      // The container may have unmounted while the bundle was downloading.
      if (!mapRef.current) {
        mapInitStartedRef.current = false;
        return;
      }

      const map = new maplibregl.Map({
        container: mapRef.current,
        style: MAP_STYLE_URL,
        center: [MAP_CENTER.lng, MAP_CENTER.lat],
        zoom: MAP_CENTER.zoom,
        attributionControl: true,
        cooperativeGestures: true,
        pitchWithRotate: false,
        dragRotate: false,
        maxPitch: 0,
        failIfMajorPerformanceCaveat: false,
        trackResize: true,
        ...mapOptionsForTier(mapTierRef.current),
      });

      map.addControl(new maplibregl.NavigationControl(), 'bottom-right');
      map.once('load', () => setMapReady(true));
      mapInstance.current = map;

      // When the side panel opens/closes the map container changes width.
      // MapLibre doesn't notice on its own, so its canvas keeps the old size
      // and the view appears to jump toward a corner. Re-sync on every resize.
      let resizeFrame;
      const ro = new ResizeObserver(() => {
        if (resizeFrame) cancelAnimationFrame(resizeFrame);
        resizeFrame = requestAnimationFrame(() => map.resize());
      });
      ro.observe(mapRef.current);
      resizeObserverRef.current = ro;
    } catch (e) {
      console.error('Failed to initialize map:', e);
      mapInitStartedRef.current = false;
      setError('The map could not start (WebGL error). Please check your browser settings.');
    }
  }, []);

  // Decide *when* to load the map, based on device tier. Runs once the dashboard
  // (and therefore the map container) is actually on screen — not while the
  // onboarding splash or auth spinner is showing.
  useEffect(() => {
    if (authLoading || !(user || isGuest)) return;

    const tier = getDeviceTier();
    mapTierRef.current = tier;

    // Metered / low-end: wait for an explicit tap so we never auto-pull ~1 MB.
    if (tier === TIERS.LOW) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDeferMap(true);
      return;
    }

    // Otherwise load after first paint during idle — sooner on capable devices.
    const cancel = onIdle(() => initMap(), tier === TIERS.HIGH ? 800 : 2000);
    return cancel;
  }, [authLoading, user, isGuest, initMap]);

  // Tear the map down on unmount.
  useEffect(
    () => () => {
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
        resizeObserverRef.current = null;
      }
      if (mapInstance.current) {
        mapInstance.current.remove();
        mapInstance.current = null;
      }
    },
    []
  );

  // Basin markers — (re)built once the map style is ready and whenever basins
  // change. Gating on `mapReady` means markers still appear even if the basin
  // data arrived before the (lazily loaded) map did.
  useEffect(() => {
    if (!mapInstance.current || !mapReady || basins.length === 0) return;

    const maplibregl = maplibreRef.current;
    if (!maplibregl) return;

    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    basins.forEach((basin) => {
      const riskColor = RISK_COLORS[basin.current_risk] || RISK_COLORS.LOW;
      const prob =
        basin.flood_probability != null
          ? `${(basin.flood_probability * 100).toFixed(0)}%`
          : '—';

      // Outer element: MapLibre owns its `transform` to position the marker on
      // the map. We must NOT write to el.style.transform ourselves — doing so
      // wipes out MapLibre's translate() and the marker jumps to the map's
      // top-left corner. So the hover animation lives on an inner node instead.
      const el = document.createElement('div');
      el.style.cssText = `
        width: 36px;
        height: 36px;
        cursor: pointer;
      `;
      el.title = basin.name;

      const inner = document.createElement('div');
      inner.style.cssText = `
        width: 100%;
        height: 100%;
        border-radius: 50%;
        background: ${riskColor};
        border: 2px solid #ffffff;
        box-shadow: 0 1px 3px rgba(35,33,28,0.35);
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-size: 11px;
        font-weight: 600;
        color: #ffffff;
        transition: transform 140ms ease, box-shadow 140ms ease;
      `;
      inner.textContent = prob;
      el.appendChild(inner);

      el.addEventListener('mouseenter', () => {
        inner.style.transform = 'scale(1.15)';
        inner.style.boxShadow = '0 3px 8px rgba(35,33,28,0.45)';
        el.style.zIndex = '10';
      });
      el.addEventListener('mouseleave', () => {
        inner.style.transform = 'scale(1)';
        inner.style.boxShadow = '0 1px 3px rgba(35,33,28,0.35)';
        el.style.zIndex = '';
      });
      el.addEventListener('click', () => selectBasin(basin));

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([basin.longitude, basin.latitude])
        .addTo(mapInstance.current);

      markersRef.current.push(marker);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [basins, mapReady]);

  // Community report pins — small, so they don't compete with basin markers
  useEffect(() => {
    if (!mapInstance.current || !mapReady) return;

    const maplibregl = maplibreRef.current;
    if (!maplibregl) return;

    reportMarkersRef.current.forEach((m) => m.remove());
    reportMarkersRef.current = [];

    reports.forEach((report) => {
      const status =
        REPORT_STATUSES.find((s) => s.value === report.status) || REPORT_STATUSES[0];

      const el = document.createElement('div');
      el.style.cssText = `
        width: 14px;
        height: 14px;
        border-radius: 50%;
        background: ${status.color};
        border: 2px solid #ffffff;
        box-shadow: 0 1px 2px rgba(35,33,28,0.3);
        cursor: pointer;
      `;
      el.title = `${status.label}${report.reporter_name ? ` — ${report.reporter_name}` : ''}`;

      const photoUrl = resolveAssetUrl(report.photo_url);
      const popupHtml = `
        <strong>${status.label}</strong>${
        report.description
          ? `<br/><span style="color:#6b6558">${escapeHtml(report.description)}</span>`
          : ''
      }${
        photoUrl
          ? `<img src="${photoUrl}" alt="Report photo" loading="lazy" style="width:180px;max-height:120px;object-fit:cover;border-radius:6px;margin-top:6px;display:block"/>`
          : ''
      }<br/><span style="color:#938c7e;font-size:11px">${
        report.reporter_name ? `by ${escapeHtml(report.reporter_name)} · ` : ''
      }${new Date(report.submitted_at).toLocaleString()}</span>`;

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([report.longitude, report.latitude])
        .setPopup(new maplibregl.Popup({ offset: 12, closeButton: false }).setHTML(popupHtml))
        .addTo(mapInstance.current);

      reportMarkersRef.current.push(marker);
    });
  }, [reports, mapReady]);

  // Role / language change: refresh only the advisory — no map movement.
  useEffect(() => {
    if (selectedBasin) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      loadForecast(selectedBasin);
    }
  }, [role, language]);

  if (authLoading) {
    return (
      <div className="loading-container" style={{ minHeight: '100vh' }}>
        <div className="spinner" />
        <span>Loading Tayari...</span>
      </div>
    );
  }

  if (!user && !isGuest) {
    return <OnboardingSplash onGuestContinue={() => setGuest(true)} />;
  }

  return (
    <div className="main-content">
      <div className="map-container">
        <div ref={mapRef} style={{ position: 'absolute', top: 0, bottom: 0, left: 0, right: 0, width: '100%' }} />

        {/* Fills the map box immediately so the largest element paints without
            waiting on WebGL — good for LCP — and holds the spot with no layout
            shift when the canvas fades in. */}
        {!mapReady && (
          <div className="map-placeholder">
            {deferMap ? (
              <div className="map-placeholder-inner">
                <div className="map-placeholder-icon" aria-hidden="true">🗺️</div>
                <p className="map-placeholder-text">
                  The interactive map uses about 1&nbsp;MB of data.
                </p>
                <button className="btn btn-primary btn-sm" onClick={initMap}>
                  Load map
                </button>
              </div>
            ) : error ? (
              <div className="map-placeholder-inner">
                <span className="map-placeholder-text">Map unavailable</span>
              </div>
            ) : (
              <div className="map-placeholder-inner">
                <div className="spinner" />
                <span className="map-placeholder-text">Loading map…</span>
              </div>
            )}
          </div>
        )}

        <div className="basin-list animate-fade-in">
          {loading && (
            <div className="basin-card" style={{ cursor: 'default' }}>
              <div className="spinner" />
              <span style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                Loading basins…
              </span>
            </div>
          )}
          {error && !loading && (
            <div className="notice notice--error" role="alert">
              {error}
            </div>
          )}
          {basins.map((basin) => (
            <div
              key={basin.id}
              className={`basin-card ${selectedBasin?.id === basin.id ? 'active' : ''}`}
              onClick={() => selectBasin(basin)}
            >
              <div
                className="basin-risk-indicator"
                style={{
                  background: `${RISK_COLORS[basin.current_risk]}1F`,
                  color: RISK_COLORS[basin.current_risk],
                  border: `1.5px solid ${RISK_COLORS[basin.current_risk]}`,
                }}
              >
                {basin.flood_probability != null
                  ? `${(basin.flood_probability * 100).toFixed(0)}%`
                  : '—'}
              </div>
              <div className="basin-info">
                <div className="basin-name">{basin.name}</div>
                <div className="basin-meta">
                  <span>{basin.country}</span>
                  <span>·</span>
                  <span className="basin-discharge">
                    {basin.current_discharge != null
                      ? `${basin.current_discharge.toFixed(0)} m³/s`
                      : '—'}
                  </span>
                </div>
              </div>
              <span
                className={`risk-badge risk-badge--${basin.current_risk?.toLowerCase()}`}
              >
                {basin.current_risk}
              </span>
            </div>
          ))}
        </div>
      </div>

      {selectedBasin && (
        <div className="side-panel">
          <button
            className="mobile-back-btn"
            onClick={() => setSelectedBasin(null)}
          >
            ← Back to map
          </button>
          {forecastLoading && !forecast ? (
            <div className="loading-container">
              <div className="spinner" />
              <span>Loading forecast…</span>
            </div>
          ) : forecast ? (
            <>
              <div>
                <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '20px', fontWeight: 600 }}>
                  {forecast.basin.name}
                </h2>
                <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                  {forecast.basin.river} · {forecast.basin.country}
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <div className="card-title">Flood risk</div>
                  <span
                    className={`risk-badge risk-badge--${forecast.risk.risk_level.toLowerCase()}`}
                  >
                    {forecast.risk.risk_level}
                  </span>
                </div>
                <RiskGauge
                  probability={forecast.risk.probability}
                  riskLevel={forecast.risk.risk_level}
                />
                <div
                  style={{
                    textAlign: 'center',
                    marginTop: '10px',
                    fontSize: '13px',
                    color: 'var(--text-muted)',
                  }}
                >
                  {forecast.risk.threshold_exceedance_days != null
                    ? `Flood threshold may be crossed in ${forecast.risk.threshold_exceedance_days} day${
                        forecast.risk.threshold_exceedance_days === 1 ? '' : 's'
                      }`
                    : 'No threshold exceedance expected in 7 days'}
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <div className="card-title">River discharge</div>
                  <span
                    style={{
                      fontSize: '12px',
                      color: 'var(--text-muted)',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    {forecast.basin.current_discharge?.toFixed(1)} m³/s
                  </span>
                </div>
                <ForecastChart discharge={forecast.discharge} />
              </div>

              <div className="card">
                <div className="card-header">
                  <div className="card-title">Impact assessment</div>
                </div>
                <ImpactPanel impact={forecast.impact} />
              </div>

              <div className="card">
                <div className="card-header">
                  <div className="card-title">Advisory</div>
                  {forecastLoading && (
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      Updating…
                    </span>
                  )}
                </div>

                <div className="form-group" style={{ marginBottom: '10px' }}>
                  <label className="form-label" htmlFor="role-select">
                    Audience
                  </label>
                  <select
                    id="role-select"
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

                <div style={{ marginBottom: '12px' }}>
                  <label
                    className="form-label"
                    style={{ marginBottom: '6px', display: 'block' }}
                  >
                    Language
                  </label>
                  <div className="lang-selector">
                    {(selectedBasin?.languages?.length
                      ? selectedBasin.languages
                      : ['en']
                    ).map((code) => (
                      <button
                        key={code}
                        className={`lang-btn ${language === code ? 'active' : ''}`}
                        onClick={() => setLanguage(code)}
                      >
                        {LANGUAGE_LABELS[code] || code}
                      </button>
                    ))}
                  </div>
                </div>

                {forecast.advisory && (
                  <AdvisoryCard
                    advisory={forecast.advisory}
                    basinId={selectedBasin?.id}
                    role={role}
                    language={language}
                  />
                )}
              </div>
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
