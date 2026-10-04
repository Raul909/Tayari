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
import LocationBar from '@/components/LocationBar';
import { loadLocation } from '@/lib/hazards';

export default function ReportPage() {
  const [place, setPlace] = useState(null);
  const [status, setStatus] = useState('water_rising');
  const [description, setDescription] = useState('');
  const [reporterName, setReporterName] = useState('');
  const [photoFile, setPhotoFile] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [reports, setReports] = useState([]);
  const [reportsLoading, setReportsLoading] = useState(true);
  const [feedBasin, setFeedBasin] = useState('all');
  const photoInputRef = useRef(null);

  const { notify } = useToast();

  // Start from the place the visitor last looked at, and never pop a location
  // permission prompt on page load. This page used to ask the moment it opened
  // and, on refusal, silently filled in Beledweyne — so a report from anywhere
  // else could be pinned to the wrong country without the reporter noticing.
  useEffect(() => {
    const saved = loadLocation();
    // Reading localStorage is the external-system sync this rule allows.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (saved) setPlace(saved);
    fetchReports()
      .then(setReports)
      .catch((err) => console.error('Failed to load reports:', err))
      .finally(() => setReportsLoading(false));
  }, []);

  async function loadReports() {
    try {
      setReports(await fetchReports());
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
    if (!place) {
      notify({
        type: 'error',
        title: 'Where is this?',
        message: 'Use your location or search for the place before sending.',
      });
      return;
    }
    setSubmitting(true);

    try {
      const fields = {
        // Reports are still grouped by river basin on the server; the reporter
        // should not have to know which one they are in.
        basin_id: nearestBasin(place.latitude, place.longitude).id,
        status,
        latitude: place.latitude,
        longitude: place.longitude,
        description: description || null,
        reporter_name: reporterName || null,
      };
      const report = photoFile
        ? await submitReportWithPhoto(fields, photoFile)
        : await submitReport(fields);
      notify({
        type: 'success',
        title: 'Report sent — thank you',
        message: `Report #${report.id} is now visible to coordinators and neighbours.`,
      });
      setDescription('');
      clearPhoto();
      loadReports();
    } catch (err) {
      notify({ type: 'error', title: 'Could not send', message: err.message });
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
        <h1 className="page-title">Report what you see</h1>
        <p className="page-description">
          Tell others what is happening on the ground. Your report — and any photo — is shared
          with coordinators and neighbours, who can reply with advice.
        </p>
      </div>

      <div className="grid-2col">
        <div className="card" style={{ alignSelf: 'start' }}>
          <form onSubmit={handleSubmit} className="report-form">
            <fieldset className="report-step">
              <legend className="report-step-title">
                <span className="report-step-num">1</span> Where are you?
              </legend>
              <LocationBar
                location={place}
                onSelect={setPlace}
                busy={false}
                currentLabel="Reporting from"
              />
            </fieldset>

            <fieldset className="report-step">
              <legend className="report-step-title">
                <span className="report-step-num">2</span> What is happening?
              </legend>
              <div className="status-options">
                {REPORT_STATUSES.map((s) => {
                  const active = status === s.value;
                  return (
                    <button
                      key={s.value}
                      type="button"
                      className={`status-option ${active ? 'active' : ''}`}
                      style={{ '--status-color': s.color }}
                      aria-pressed={active}
                      onClick={() => setStatus(s.value)}
                    >
                      {s.label}
                    </button>
                  );
                })}
              </div>
            </fieldset>

            <fieldset className="report-step">
              <legend className="report-step-title">
                <span className="report-step-num">3</span> Add details{' '}
                <span className="report-step-optional">optional</span>
              </legend>

              <input
                ref={photoInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handlePhotoChange}
                style={{ display: 'none' }}
                aria-label="Photo of the conditions"
              />
              {photoPreview ? (
                <div>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={photoPreview} alt="Your photo" className="report-photo-preview" />
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
                  className="btn btn-ghost report-photo-btn"
                  onClick={() => photoInputRef.current?.click()}
                >
                  <span aria-hidden="true">📷</span> Take or choose a photo
                </button>
              )}

              <div className="form-group">
                <label className="form-label" htmlFor="desc">
                  What do you see?
                </label>
                <textarea
                  id="desc"
                  className="form-textarea"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Water is over the road by the market bridge"
                  rows={3}
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="reporter">
                  Your name
                </label>
                <input
                  id="reporter"
                  className="form-input"
                  type="text"
                  autoComplete="name"
                  value={reporterName}
                  onChange={(e) => setReporterName(e.target.value)}
                  placeholder="e.g. Ahmed"
                />
              </div>
            </fieldset>

            <button
              className="btn btn-primary btn-lg"
              type="submit"
              disabled={submitting || !place}
            >
              {submitting ? 'Sending…' : place ? 'Send report' : 'Choose a place to send'}
            </button>
          </form>
        </div>

        <div className="card" style={{ alignSelf: 'start' }}>
          <div className="card-header">
            <h2 className="card-title">Recent reports</h2>
            <select
              className="form-select report-feed-filter"
              value={feedBasin}
              onChange={(e) => setFeedBasin(e.target.value)}
              aria-label="Filter reports by area"
            >
              <option value="all">All areas</option>
              {Object.values(BASINS).map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          </div>

          {reportsLoading ? (
            <div className="loading-container">
              <div className="spinner" />
            </div>
          ) : visibleReports.length === 0 ? (
            <div className="empty-state">No reports here yet. Be the first to report.</div>
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

/** The calibrated basin closest to a point — reports are grouped by it. */
function nearestBasin(latitude, longitude) {
  let best = null;
  let bestDist = Infinity;
  for (const basin of Object.values(BASINS)) {
    const d = (basin.lat - latitude) ** 2 + (basin.lng - longitude) ** 2;
    if (d < bestDist) {
      best = basin;
      bestDist = d;
    }
  }
  return best;
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
