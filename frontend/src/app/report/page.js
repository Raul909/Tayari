'use client';

import { useState, useEffect, useRef } from 'react';
import {
  submitReport,
  submitReportWithPhoto,
  submitAdvice,
  fetchReports,
  resolveAssetUrl,
} from '@/lib/api';
import { BASINS, REPORT_STATUSES } from '@/lib/constants';
import { useToast } from '@/components/Toast';

export default function ReportPage() {
  const [basinId, setBasinId] = useState('shabelle');
  const [status, setStatus] = useState('water_rising');
  const [description, setDescription] = useState('');
  const [reporterName, setReporterName] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [photoFile, setPhotoFile] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [reports, setReports] = useState([]);
  const [feedBasin, setFeedBasin] = useState('all');
  const [geoError, setGeoError] = useState(null);
  const [locating, setLocating] = useState(false);
  const photoInputRef = useRef(null);

  const { notify } = useToast();

  useEffect(() => {
    loadReports();
    getLocation();
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

  function handlePhotoChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhotoFile(file);
    setPhotoPreview(URL.createObjectURL(file));
  }

  function clearPhoto() {
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhotoFile(null);
    setPhotoPreview(null);
    if (photoInputRef.current) photoInputRef.current.value = '';
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);

    try {
      const fields = {
        basin_id: basinId,
        status,
        latitude: parseFloat(latitude),
        longitude: parseFloat(longitude),
        description: description || null,
        reporter_name: reporterName || null,
      };
      const report = photoFile
        ? await submitReportWithPhoto(fields, photoFile)
        : await submitReport(fields);
      notify({
        type: 'success',
        title: 'Report submitted',
        message: `Report #${report.id} recorded. It now shows on the dashboard map.`,
      });
      setDescription('');
      clearPhoto();
      loadReports();
    } catch (err) {
      notify({ type: 'error', title: 'Could not submit', message: err.message });
    } finally {
      setSubmitting(false);
    }
  }

  function handleReportUpdated(updated) {
    setReports((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
  }

  const visibleReports = reports
    .filter((r) => feedBasin === 'all' || r.basin_id === feedBasin)
    .slice()
    .reverse()
    .slice(0, 20);

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Community reports</h1>
        <p className="page-description">
          Report ground conditions from the field, see what others are reporting, and respond
          with advice. Reports appear as pins on the dashboard map and serve as ground truth
          for the forecasts.
        </p>
      </div>

      <div style={{ display: 'grid', gap: '20px', gridTemplateColumns: '1fr 1fr' }}>
        <div className="card" style={{ alignSelf: 'start' }}>
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

            <div className="form-group">
              <label className="form-label">Photo of the conditions (optional)</label>
              <input
                ref={photoInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handlePhotoChange}
                style={{ display: 'none' }}
              />
              {photoPreview ? (
                <div style={{ position: 'relative' }}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={photoPreview}
                    alt="Report preview"
                    style={{
                      width: '100%',
                      maxHeight: '220px',
                      objectFit: 'cover',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border-color)',
                    }}
                  />
                  <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => photoInputRef.current?.click()}
                    >
                      Retake
                    </button>
                    <button type="button" className="btn btn-ghost btn-sm" onClick={clearPhoto}>
                      Remove
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => photoInputRef.current?.click()}
                  style={{
                    border: '1px dashed var(--border-strong)',
                    padding: '18px',
                    width: '100%',
                  }}
                >
                  📷 Take or choose a photo
                </button>
              )}
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

        <div className="card" style={{ alignSelf: 'start' }}>
          <div className="card-header">
            <div className="card-title">Reports from the field</div>
            <select
              className="form-select"
              value={feedBasin}
              onChange={(e) => setFeedBasin(e.target.value)}
              style={{ width: 'auto', fontSize: '12px', padding: '4px 8px' }}
            >
              <option value="all">All basins</option>
              {Object.values(BASINS).map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          </div>

          {visibleReports.length === 0 ? (
            <div className="empty-state">No community reports yet. Be the first to report.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {visibleReports.map((r) => (
                <ReportCard
                  key={r.id}
                  report={r}
                  onUpdated={handleReportUpdated}
                  notify={notify}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ReportCard({ report, onUpdated, notify }) {
  const [showAdviceForm, setShowAdviceForm] = useState(false);
  const [adviceMessage, setAdviceMessage] = useState('');
  const [adviceName, setAdviceName] = useState('');
  const [sending, setSending] = useState(false);

  const statusInfo =
    REPORT_STATUSES.find((s) => s.value === report.status) || REPORT_STATUSES[0];
  const basinName = BASINS[report.basin_id]?.name || report.basin_id;
  const photoUrl = resolveAssetUrl(report.photo_url);
  const advice = report.advice || [];

  async function handleAdviceSubmit(e) {
    e.preventDefault();
    if (adviceMessage.trim().length < 2) return;
    setSending(true);
    try {
      const updated = await submitAdvice(report.id, {
        message: adviceMessage.trim(),
        author_name: adviceName.trim() || null,
      });
      onUpdated(updated);
      setAdviceMessage('');
      setShowAdviceForm(false);
      notify({
        type: 'success',
        title: 'Advice sent',
        message: `Your guidance is now attached to report #${report.id}.`,
      });
    } catch (err) {
      notify({ type: 'error', title: 'Could not send advice', message: err.message });
    } finally {
      setSending(false);
    }
  }

  return (
    <div
      style={{
        background: 'var(--surface-sunken)',
        border: '1px solid var(--border-color)',
        borderRadius: 'var(--radius-sm)',
        padding: '12px',
        borderLeft: `3px solid ${statusInfo.color}`,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '13px', fontWeight: 600 }}>{statusInfo.label}</span>
        <span
          style={{
            fontSize: '11px',
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono)',
          }}
        >
          {new Date(report.submitted_at).toLocaleString()}
        </span>
      </div>

      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
        {basinName}
      </div>

      {photoUrl && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={photoUrl}
          alt={`Report #${report.id} conditions`}
          loading="lazy"
          style={{
            width: '100%',
            maxHeight: '200px',
            objectFit: 'cover',
            borderRadius: 'var(--radius-sm)',
            marginTop: '8px',
            border: '1px solid var(--border-color)',
          }}
        />
      )}

      {report.description && (
        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '6px' }}>
          {report.description}
        </div>
      )}
      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
        {report.latitude.toFixed(4)}, {report.longitude.toFixed(4)}
        {report.reporter_name && ` · by ${report.reporter_name}`}
      </div>

      {advice.length > 0 && (
        <div
          style={{
            marginTop: '10px',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
          }}
        >
          {advice.map((a) => (
            <div
              key={a.id}
              style={{
                background: 'var(--surface)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-sm)',
                padding: '8px 10px',
                fontSize: '12px',
              }}
            >
              <div style={{ color: 'var(--text-secondary)' }}>{a.message}</div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '3px' }}>
                💬 {a.author_name || 'Responder'} ·{' '}
                {new Date(a.created_at).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      )}

      {showAdviceForm ? (
        <form
          onSubmit={handleAdviceSubmit}
          style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}
        >
          <textarea
            className="form-textarea"
            value={adviceMessage}
            onChange={(e) => setAdviceMessage(e.target.value)}
            placeholder="e.g. The bridge at the market is already closed — use the northern road to reach high ground."
            rows={2}
            required
          />
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              className="form-input"
              type="text"
              value={adviceName}
              onChange={(e) => setAdviceName(e.target.value)}
              placeholder="Your name (optional)"
              style={{ flex: 1 }}
            />
            <button className="btn btn-primary btn-sm" type="submit" disabled={sending}>
              {sending ? 'Sending…' : 'Send'}
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => setShowAdviceForm(false)}
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          style={{ marginTop: '10px' }}
          onClick={() => setShowAdviceForm(true)}
        >
          💬 Give advice{advice.length > 0 ? ` (${advice.length})` : ''}
        </button>
      )}
    </div>
  );
}
