'use client';

import { useRef, useEffect, useState, useCallback } from 'react';
import maplibregl from 'maplibre-gl';
import { fetchBasins, fetchForecast } from '@/lib/api';
import { RISK_COLORS, MAP_CENTER, ROLES, LANGUAGES } from '@/lib/constants';
import RiskGauge from '@/components/RiskGauge';
import ForecastChart from '@/components/ForecastChart';
import AdvisoryCard from '@/components/AdvisoryCard';
import ImpactPanel from '@/components/ImpactPanel';

export default function Dashboard() {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const markersRef = useRef([]);

  const [basins, setBasins] = useState([]);
  const [selectedBasin, setSelectedBasin] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(true);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [role, setRole] = useState('general');
  const [language, setLanguage] = useState('en');
  const [error, setError] = useState(null);

  // Load basins on mount
  useEffect(() => {
    loadBasins();
  }, []);

  async function loadBasins() {
    try {
      setLoading(true);
      const data = await fetchBasins();
      setBasins(data);
      setError(null);
    } catch (err) {
      console.error('Failed to load basins:', err);
      setError('Failed to connect to Tayari API. Is the backend running on port 8000?');
    } finally {
      setLoading(false);
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
      console.error("Failed to initialize map:", e);
      setError("Failed to initialize map due to a WebGL error. Please check your browser settings.");
    }

    return () => {
      if (mapInstance.current) {
        mapInstance.current.remove();
        mapInstance.current = null;
      }
    };
  }, []);

  // Add basin markers when basins are loaded
  useEffect(() => {
    if (!mapInstance.current || basins.length === 0) return;

    // Clear existing markers
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    basins.forEach((basin) => {
      const riskColor = RISK_COLORS[basin.current_risk] || RISK_COLORS.LOW;
      const prob = basin.flood_probability != null
        ? `${(basin.flood_probability * 100).toFixed(0)}%`
        : '—';

      // Create pulsing marker element
      const el = document.createElement('div');
      el.style.cssText = `
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: ${riskColor};
        border: 3px solid white;
        box-shadow: 0 0 16px ${riskColor}80, 0 2px 8px rgba(0,0,0,0.3);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Roboto Mono', monospace;
        font-size: 11px;
        font-weight: 700;
        color: white;
        transition: transform 0.2s;
        position: relative;
      `;
      el.textContent = prob;
      el.title = basin.name;

      // Pulse ring
      const ring = document.createElement('div');
      ring.style.cssText = `
        position: absolute;
        inset: -6px;
        border-radius: 50%;
        border: 2px solid ${riskColor};
        opacity: 0.4;
        animation: ripple 2s infinite;
      `;
      el.appendChild(ring);

      el.addEventListener('mouseenter', () => {
        el.style.transform = 'scale(1.15)';
      });
      el.addEventListener('mouseleave', () => {
        el.style.transform = 'scale(1)';
      });
      el.addEventListener('click', () => {
        selectBasin(basin);
      });

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([basin.longitude, basin.latitude])
        .addTo(mapInstance.current);

      markersRef.current.push(marker);
    });
  }, [basins]);

  const selectBasin = useCallback(
    async (basin) => {
      setSelectedBasin(basin);
      setForecastLoading(true);

      // Fly to basin
      if (mapInstance.current) {
        mapInstance.current.flyTo({
          center: [basin.longitude, basin.latitude],
          zoom: 9,
          duration: 1500,
          essential: true,
        });
      }

      try {
        const data = await fetchForecast(basin.id, role, language);
        setForecast(data);
      } catch (err) {
        console.error('Failed to load forecast:', err);
      } finally {
        setForecastLoading(false);
      }
    },
    [role, language]
  );

  // Reload advisory when role or language changes
  useEffect(() => {
    if (selectedBasin) {
      selectBasin(selectedBasin);
    }
  }, [role, language]);

  return (
    <div className="main-content">
      {/* Map */}
      <div className="map-container">
        <div ref={mapRef} style={{ width: '100%', height: '100%' }} />

        {/* Basin cards overlay */}
        <div className="basin-list animate-fade-in">
          {loading && (
            <div className="basin-card">
              <div className="spinner" />
              <span style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                Loading basins...
              </span>
            </div>
          )}
          {error && (
            <div className="basin-card" style={{ borderColor: 'var(--risk-high)' }}>
              <span style={{ color: 'var(--risk-high)', fontSize: '13px' }}>
                ⚠️ {error}
              </span>
            </div>
          )}
          {basins.map((basin) => (
            <div
              key={basin.id}
              className={`basin-card ${
                selectedBasin?.id === basin.id ? 'active' : ''
              }`}
              onClick={() => selectBasin(basin)}
            >
              <div
                className="basin-risk-indicator"
                style={{
                  background: `${RISK_COLORS[basin.current_risk]}20`,
                  color: RISK_COLORS[basin.current_risk],
                  border: `2px solid ${RISK_COLORS[basin.current_risk]}`,
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
                  <span>•</span>
                  <span className="basin-discharge">
                    {basin.current_discharge != null
                      ? `${basin.current_discharge.toFixed(0)} m³/s`
                      : '—'}
                  </span>
                </div>
                <span
                  className={`risk-badge risk-badge--${basin.current_risk?.toLowerCase()}`}
                  style={{ marginTop: '4px' }}
                >
                  <span
                    className={`risk-dot risk-dot--${basin.current_risk?.toLowerCase()}`}
                  />
                  {basin.current_risk}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Side Panel */}
      {selectedBasin && (
        <div className="side-panel animate-slide-in">
          {forecastLoading ? (
            <div className="loading-container">
              <div className="spinner" />
              <span>Loading forecast...</span>
            </div>
          ) : forecast ? (
            <>
              {/* Basin header */}
              <div>
                <h2 style={{ fontSize: '18px', fontWeight: 700 }}>
                  {forecast.basin.name}
                </h2>
                <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                  {forecast.basin.river} · {forecast.basin.country}
                </div>
              </div>

              {/* Risk Gauge */}
              <div className="card">
                <div className="card-header">
                  <div className="card-title">🎯 Flood Risk</div>
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
                    marginTop: '8px',
                    fontSize: '13px',
                    color: 'var(--text-muted)',
                  }}
                >
                  {forecast.risk.threshold_exceedance_days != null
                    ? `Threshold may be exceeded in ${forecast.risk.threshold_exceedance_days} days`
                    : 'No threshold exceedance expected in 7 days'}
                </div>
              </div>

              {/* Discharge Chart */}
              <div className="card">
                <div className="card-header">
                  <div className="card-title">📈 River Discharge</div>
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

              {/* Impact Panel */}
              <div className="card">
                <div className="card-header">
                  <div className="card-title">👥 Impact Assessment</div>
                </div>
                <ImpactPanel impact={forecast.impact} />
              </div>

              {/* Advisory with role & language selectors */}
              <div className="card">
                <div className="card-header">
                  <div className="card-title">📢 Advisory</div>
                </div>

                {/* Role selector */}
                <div className="form-group" style={{ marginBottom: '10px' }}>
                  <label className="form-label">Role</label>
                  <select
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

                {/* Language selector */}
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
                        {l.flag} {l.label}
                      </button>
                    ))}
                  </div>
                </div>

                {forecast.advisory && (
                  <AdvisoryCard advisory={forecast.advisory} />
                )}
              </div>
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}
