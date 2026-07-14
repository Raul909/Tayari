'use client';

import { useState, useEffect } from 'react';
import { submitReport, fetchReports } from '@/lib/api';
import { BASINS, REPORT_STATUSES } from '@/lib/constants';

export default function ReportPage() {
  const [basinId, setBasinId] = useState('shabelle');
  const [status, setStatus] = useState('water_rising');
  const [description, setDescription] = useState('');
  const [reporterName, setReporterName] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [reports, setReports] = useState([]);
  const [geoError, setGeoError] = useState(null);

  useEffect(() => {
    loadReports();
    getLocation();
  }, []);

  function getLocation() {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLatitude(pos.coords.latitude.toFixed(6));
          setLongitude(pos.coords.longitude.toFixed(6));
        },
        (err) => {
          setGeoError('Location access denied. Enter coordinates manually.');
          // Default to Beledweyne
          setLatitude('4.74');
          setLongitude('45.20');
        }
      );
    } else {
      setLatitude('4.74');
      setLongitude('45.20');
    }
  }

  async function loadReports() {
    try {
      const data = await fetchReports();
      setReports(data);
    } catch (err) {
      console.error('Failed to load reports:', err);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setResult(null);

    try {
      const report = await submitReport({
        basin_id: basinId,
        status,
        latitude: parseFloat(latitude),
        longitude: parseFloat(longitude),
        description: description || null,
        reporter_name: reporterName || null,
      });
      setResult({ success: true, report });
      setDescription('');
      loadReports();
    } catch (err) {
      setResult({ success: false, message: err.message });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">📋 Community Report</h1>
        <p className="page-description">
          Submit ground conditions from the field. Your report helps verify
          forecasts and alerts your community. Reports appear as pins on the
          dashboard map.
        </p>
      </div>

      <div style={{ display: 'grid', gap: '24px', gridTemplateColumns: '1fr 1fr' }}>
        {/* Submit Report */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Submit Report</div>
          </div>

          <form
            onSubmit={handleSubmit}
            style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}
          >
            <div className="form-group">
              <label className="form-label">Basin</label>
              <select
                className="form-select"
                value={basinId}
                onChange={(e) => setBasinId(e.target.value)}
              >
                {Object.values(BASINS).map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Current Situation</label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {REPORT_STATUSES.map((s) => (
                  <button
                    key={s.value}
                    type="button"
                    className={`btn ${status === s.value ? 'btn-primary' : 'btn-ghost'}`}
                    style={{
                      fontSize: '13px',
                      ...(status === s.value
                        ? { background: s.color, boxShadow: `0 0 12px ${s.color}40` }
                        : {}),
                    }}
                    onClick={() => setStatus(s.value)}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div className="form-group">
                <label className="form-label">Latitude</label>
                <input
                  className="form-input"
                  type="number"
                  step="0.000001"
                  value={latitude}
                  onChange={(e) => setLatitude(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Longitude</label>
                <input
                  className="form-input"
                  type="number"
                  step="0.000001"
                  value={longitude}
                  onChange={(e) => setLongitude(e.target.value)}
                  required
                />
              </div>
            </div>
            {geoError && (
              <span style={{ fontSize: '11px', color: 'var(--risk-moderate)' }}>
                ⚠️ {geoError}
              </span>
            )}

            <div className="form-group">
              <label className="form-label">Your Name (optional)</label>
              <input
                className="form-input"
                type="text"
                value={reporterName}
                onChange={(e) => setReporterName(e.target.value)}
                placeholder="e.g., Ahmed"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Description (optional)</label>
              <textarea
                className="form-textarea"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what you're seeing..."
                rows={3}
              />
            </div>

            <button
              className="btn btn-primary btn-lg"
              type="submit"
              disabled={submitting}
            >
              {submitting ? 'Submitting...' : '📍 Submit Report'}
            </button>

            {result && (
              <div
                className="card"
                style={{
                  borderColor: result.success
                    ? 'var(--risk-low)'
                    : 'var(--risk-high)',
                  padding: '14px',
                }}
              >
                <div style={{ fontSize: '14px', fontWeight: 600 }}>
                  {result.success ? '✅ Report Submitted' : '❌ Failed'}
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  {result.success
                    ? `Report #${result.report.id} recorded at (${result.report.latitude}, ${result.report.longitude})`
                    : result.message}
                </div>
              </div>
            )}
          </form>
        </div>

        {/* Recent Reports */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Recent Reports</div>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              {reports.length} total
            </span>
          </div>

          {reports.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontSize: '14px', textAlign: 'center', padding: '30px' }}>
              No community reports yet. Be the first to report!
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {reports
                .slice()
                .reverse()
                .slice(0, 10)
                .map((r) => {
                  const statusInfo = REPORT_STATUSES.find(
                    (s) => s.value === r.status
                  ) || REPORT_STATUSES[0];
                  return (
                    <div
                      key={r.id}
                      style={{
                        background: 'rgba(0,0,0,0.2)',
                        borderRadius: '10px',
                        padding: '12px',
                        borderLeft: `3px solid ${statusInfo.color}`,
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '13px', fontWeight: 600 }}>
                          {statusInfo.label}
                        </span>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                          {new Date(r.submitted_at).toLocaleTimeString()}
                        </span>
                      </div>
                      {r.description && (
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                          {r.description}
                        </div>
                      )}
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                        📍 {r.latitude.toFixed(4)}, {r.longitude.toFixed(4)}
                        {r.reporter_name && ` · by ${r.reporter_name}`}
                      </div>
                    </div>
                  );
                })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
