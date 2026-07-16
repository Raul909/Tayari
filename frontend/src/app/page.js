'use client';

import { useRef, useEffect, useState, useCallback } from 'react';
import maplibregl from 'maplibre-gl';
import { fetchBasins, fetchForecast, fetchReports, resolveAssetUrl } from '@/lib/api';
import { RISK_COLORS, MAP_CENTER, ROLES, LANGUAGES, REPORT_STATUSES } from '@/lib/constants';
import { useToast } from '@/components/Toast';
import RiskGauge from '@/components/RiskGauge';
import ForecastChart from '@/components/ForecastChart';
import AdvisoryCard from '@/components/AdvisoryCard';
import ImpactPanel from '@/components/ImpactPanel';

export default function Dashboard() {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const markersRef = useRef([]);
  const reportMarkersRef = useRef([]);
  // Monotonic token so a slow forecast response can't overwrite a newer one.
  const forecastReqId = useRef(0);

  const [basins, setBasins] = useState([]);
  const [reports, setReports] = useState([]);
  const [selectedBasin, setSelectedBasin] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(true);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [role, setRole] = useState('general');
  const [language, setLanguage] = useState('en');
  const [error, setError] = useState(null);

  // Refs mirror role/language so map markers (created once) always read the
  // current values instead of a value captured when the marker was made.
  const roleRef = useRef(role);
  const languageRef = useRef(language);
  useEffect(() => {
    roleRef.current = role;
    languageRef.current = language;
  }, [role, language]);

  const { notify } = useToast();

  // Load basins + community reports on mount
  useEffect(() => {
    loadBasins();
    loadReports();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  // Initialize map
  useEffect(() => {
    if (!mapRef.current || mapInstance.current) return;

    try {
      const map = new maplibregl.Map({
        container: mapRef.current,
        style: 'https://tiles.openfreemap.org/styles/positron',
        center: [MAP_CENTER.lng, MAP_CENTER.lat],
        zoom: MAP_CENTER.zoom,
        attributionControl: true,
      });

      map.addControl(new maplibregl.NavigationControl(), 'bottom-right');
      mapInstance.current = map;
    } catch (e) {
      console.error('Failed to initialize map:', e);
      setError('The map could not start (WebGL error). Please check your browser settings.');
    }

    return () => {
      if (mapInstance.current) {
        mapInstance.current.remove();
        mapInstance.current = null;
      }
    };
  }, []);

  // Basin markers
  useEffect(() => {
    if (!mapInstance.current || basins.length === 0) return;

    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    basins.forEach((basin) => {
      const riskColor = RISK_COLORS[basin.current_risk] || RISK_COLORS.LOW;
      const prob =
        basin.flood_probability != null
          ? `${(basin.flood_probability * 100).toFixed(0)}%`
          : '—';

      const el = document.createElement('div');
      el.style.cssText = `
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: ${riskColor};
        border: 2px solid #ffffff;
        box-shadow: 0 1px 3px rgba(35,33,28,0.35);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-size: 11px;
        font-weight: 600;
        color: #ffffff;
        transition: transform 140ms ease;
      `;
      el.textContent = prob;
      el.title = basin.name;

      el.addEventListener('mouseenter', () => {
        el.style.transform = 'scale(1.1)';
      });
      el.addEventListener('mouseleave', () => {
        el.style.transform = 'scale(1)';
      });
      el.addEventListener('click', () => selectBasin(basin));

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([basin.longitude, basin.latitude])
        .addTo(mapInstance.current);

      markersRef.current.push(marker);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [basins]);

  // Community report pins — small, so they don't compete with basin markers
  useEffect(() => {
    if (!mapInstance.current) return;

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reports]);

  // Fetch a basin's forecast without moving the map. Guarded against races,
  // and always reads the current role/language from refs.
  const loadForecast = useCallback(
    async (basin) => {
      const reqId = ++forecastReqId.current;
      setForecastLoading(true);
      try {
        const data = await fetchForecast(basin.id, roleRef.current, languageRef.current);
        // Ignore if a newer request has since started.
        if (reqId === forecastReqId.current) {
          setForecast(data);
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
    },
    [notify]
  );

  // Select a basin: fly the map to it, then load its forecast.
  const selectBasin = useCallback(
    (basin) => {
      setSelectedBasin(basin);
      if (mapInstance.current) {
        mapInstance.current.flyTo({
          center: [basin.longitude, basin.latitude],
          zoom: 9,
          duration: 1400,
          essential: true,
        });
      }
      loadForecast(basin);
    },
    [loadForecast]
  );

  // Role / language change: refresh only the advisory — no map movement.
  useEffect(() => {
    if (selectedBasin) {
      loadForecast(selectedBasin);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role, language]);

  return (
    <div className="main-content">
      <div className="map-container">
        <div ref={mapRef} style={{ position: 'absolute', top: 0, bottom: 0, left: 0, right: 0, width: '100%' }} />

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
                    {LANGUAGES.map((l) => (
                      <button
                        key={l.value}
                        className={`lang-btn ${language === l.value ? 'active' : ''}`}
                        onClick={() => setLanguage(l.value)}
                      >
                        {l.label}
                      </button>
                    ))}
                  </div>
                </div>

                {forecast.advisory && <AdvisoryCard advisory={forecast.advisory} />}
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
