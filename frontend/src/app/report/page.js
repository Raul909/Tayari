'use client';

import { useState, useEffect } from 'react';
import { submitReport, fetchReports } from '@/lib/api';
import { BASINS, REPORT_STATUSES } from '@/lib/constants';
import { useToast } from '@/components/Toast';

export default function ReportPage() {
  const [basinId, setBasinId] = useState('shabelle');
  const [status, setStatus] = useState('water_rising');
  const [description, setDescription] = useState('');
  const [reporterName, setReporterName] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [reports, setReports] = useState([]);
  const [geoError, setGeoError] = useState(null);
  const [locating, setLocating] = useState(false);

  const { notify } = useToast();

  useEffect(() => {
    loadReports();
    getLocation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function getLocation() {
    if ('geolocation' in navigator) {
      setLocating(true);
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLatitude(pos.coords.latitude.toFixed(6));
          setLongitude(pos.coords.longitude.toFixed(6));
          setGeoError(null);
          setLocating(false);
        },
        () => {
          setGeoError('Location access denied — enter coordinates manually.');
          // Fall back to Beledweyne so the field is never empty.
          setLatitude('4.74');
          setLongitude('45.20');
          setLocating(false);
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

    try {
      const report = await submitReport({
        basin_id: basinId,
        status,
        latitude: parseFloat(latitude),
        longitude: parseFloat(longitude),
        description: description || null,
        reporter_name: reporterName || null,
      });
      notify({
        type: 'success',
        title: 'Report submitted',
        message: `Report #${report.id} recorded. It now shows on the dashboard map.`,
      });
      setDescription('');
      loadReports();
    } catch (err) {
      notify({ type: 'error', title: 'Could not submit', message: err.message });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Community report</h1>
        <p className="page-description">
          Report ground conditions from the field. Your report helps verify forecasts and
          appears as a pin on the dashboard map.
        </p>
      </div>

      <div style={{ display: 'grid', gap: '20px', gridTemplateColumns: '1fr 1fr' }}>
        <div className="card">
          <div className="card-header">
            <div className="card-title">Submit a report</div>
          </div>

          <form
            onSubmit={handleSubmit}
            style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}
          >
            <div className="form-group">
              <label className="form-label" htmlFor="r-basin">Basin</label>
              <select
                id="r-basin"
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
              <label className="form-label">Current situation</label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {REPORT_STATUSES.map((s) => {
                  const active = status === s.value;
                  return (
                    <button
                      key={s.value}
                      type="button"
                      className="btn btn-sm"
                      style={
                        active
                          ? { background: s.color, color: '#fff', borderColor: s.color }
                          : {
                              background: 'var(--surface)',
                              color: 'var(--text-secondary)',
                              borderColor: 'var(--border-strong)',
                            }
                      }
                      onClick={() => setStatus(s.value)}
                    >
                      {s.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div className="form-group">
                <label className="form-label" htmlFor="lat">Latitude</label>
                <input
                  id="lat"
                  className="form-input"
                  type="number"
                  step="0.000001"
                  value={latitude}
                  onChange={(e) => setLatitude(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="lng">Longitude</label>
                <input
                  id="lng"
                  className="form-input"
                  type="number"
                  step="0.000001"
                  value={longitude}
                  onChange={(e) => setLongitude(e.target.value)}
                  required
                />
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={getLocation}
                disabled={locating}
              >
                {locating ? 'Locating…' : 'Use my location'}
              </button>
              {geoError && (
                <span style={{ fontSize: '12px', color: 'var(--risk-moderate)' }}>
                  {geoError}
                </span>
              )}
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="reporter">Your name (optional)</label>
              <input
                id="reporter"
                className="form-input"
                type="text"
                value={reporterName}
                onChange={(e) => setReporterName(e.target.value)}
                placeholder="e.g. Ahmed"
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="desc">Description (optional)</label>
              <textarea
                id="desc"
                className="form-textarea"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what you're seeing…"
                rows={3}
              />
            </div>

            <button className="btn btn-primary btn-lg" type="submit" disabled={submitting}>
              {submitting ? 'Submitting…' : 'Submit report'}
            </button>
          </form>
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">Recent reports</div>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              {reports.length} total
            </span>
          </div>

          {reports.length === 0 ? (
            <div className="empty-state">No community reports yet. Be the first to report.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {reports
                .slice()
                .reverse()
                .slice(0, 10)
                .map((r) => {
                  const statusInfo =
                    REPORT_STATUSES.find((s) => s.value === r.status) || REPORT_STATUSES[0];
                  return (
                    <div
                      key={r.id}
                      style={{
                        background: 'var(--surface-sunken)',
                        border: '1px solid var(--border-color)',
                        borderRadius: 'var(--radius-sm)',
                        padding: '12px',
                        borderLeft: `3px solid ${statusInfo.color}`,
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                        }}
                      >
                        <span style={{ fontSize: '13px', fontWeight: 600 }}>
                          {statusInfo.label}
                        </span>
                        <span
                          style={{
                            fontSize: '11px',
                            color: 'var(--text-muted)',
                            fontFamily: 'var(--font-mono)',
                          }}
                        >
                          {new Date(r.submitted_at).toLocaleTimeString()}
                        </span>
                      </div>
                      {r.description && (
                        <div
                          style={{
                            fontSize: '12px',
                            color: 'var(--text-secondary)',
                            marginTop: '4px',
                          }}
                        >
                          {r.description}
                        </div>
                      )}
                      <div
                        style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}
                      >
                        {r.latitude.toFixed(4)}, {r.longitude.toFixed(4)}
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
