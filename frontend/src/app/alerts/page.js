'use client';

import { useEffect, useRef, useState } from 'react';
import LocationBar from '@/components/LocationBar';
import AuthModal from '@/components/AuthModal';
import { useToast } from '@/components/Toast';
import { useAuth } from '@/lib/auth';
import { getSupabase } from '@/lib/supabase';
import { fetchAlertHistory } from '@/lib/api';
import { LANGUAGE_LABELS, ROLES } from '@/lib/constants';
import {
  fetchHazardAdvisory,
  fetchHazardProfile,
  fetchHazardTypes,
  hazardMeta,
  loadLocation,
  placeLabel,
  reverseGeocode,
  saveLocation,
  sendHazardAlert,
} from '@/lib/hazards';

// Loose E.164 check (+ then 8-15 digits) — enough to catch a typo or a pasted
// wrong thing before it reaches Twilio and costs a message.
const PHONE_RE = /^\+[1-9]\d{7,14}$/;

/**
 * Sending an advisory to a phone.
 *
 * Reordered around the question people actually arrive with. This page used to
 * open with a dropdown of eight river basins, which meant the only alert you
 * could send was a flood alert, and only for one of eight rivers. The flow is
 * now hazard first, then place: pick what you are worried about, pick where,
 * and Tayari works out whether that hazard is even relevant there.
 */
export default function AlertsPage() {
  const { user, loading: authLoading, logout } = useAuth();
  const [showAuthModal, setShowAuthModal] = useState(false);

  const [catalog, setCatalog] = useState([]);
  const [hazard, setHazard] = useState(null);
  const [location, setLocation] = useState(null);
  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);

  const [role, setRole] = useState('general');
  const [language, setLanguage] = useState('en');
  const [phoneNumber, setPhoneNumber] = useState('');

  const [preview, setPreview] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);

  const [sending, setSending] = useState(false);
  const [history, setHistory] = useState([]);

  const { notify } = useToast();
  const profileReq = useRef(0);
  const previewReq = useRef(0);

  // ── Catalog, saved location, history ────────────────────────────────────
  useEffect(() => {
    fetchHazardTypes()
      .then((data) => {
        const list = data.hazards || [];
        setCatalog(list);
        const wanted = new URLSearchParams(window.location.search).get('hazard');
        setHazard(list.find((h) => h.hazard === wanted)?.hazard || list[0]?.hazard || null);
      })
      .catch(() => {});

    const saved = loadLocation();
    if (saved) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLocation(saved);
    }

    fetchAlertHistory()
      .then(setHistory)
      .catch(() => {});
  }, []);

  // ── Assess the chosen location ──────────────────────────────────────────
  useEffect(() => {
    if (!location) return;
    const id = ++profileReq.current;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setProfileLoading(true);

    (async () => {
      try {
        let target = location;
        if (!target.name) {
          const named = await reverseGeocode(target.latitude, target.longitude);
          if (named) target = { ...target, ...named };
        }
        const data = await fetchHazardProfile(target);
        if (id !== profileReq.current) return;
        setProfile(data);
        const resolved = { ...target, ...data.location };
        setLocation(resolved);
        saveLocation(resolved);
        // Only offer languages actually spoken at this location.
        if (!(data.languages || ['en']).includes(language)) setLanguage('en');
      } catch {
        if (id === profileReq.current) setProfile(null);
      } finally {
        if (id === profileReq.current) setProfileLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location?.latitude, location?.longitude]);

  // ── Preview the exact SMS that will be sent ─────────────────────────────
  const relevant = profile?.hazards?.some((h) => h.hazard === hazard);

  useEffect(() => {
    if (!hazard || !location || !profile || !relevant) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPreview('');
      return;
    }
    const id = ++previewReq.current;
    const controller = new AbortController();
    setPreviewLoading(true);
    setPreviewError(null);

    fetchHazardAdvisory(hazard, location, { role, language, signal: controller.signal })
      .then((data) => {
        if (id !== previewReq.current) return;
        setPreview(data.sms_text || '');
      })
      .catch((e) => {
        if (id !== previewReq.current || e.name === 'AbortError') return;
        setPreviewError('Could not generate a preview.');
        setPreview('');
      })
      .finally(() => {
        if (id === previewReq.current) setPreviewLoading(false);
      });

    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hazard, location?.latitude, location?.longitude, role, language, relevant, profile]);

  async function handleSend() {
    const phones = phoneNumber.split(',').map((p) => p.trim()).filter(Boolean);
    if (phones.length === 0) {
      notify({ type: 'error', title: 'No recipients', message: 'Enter at least one phone number.' });
      return;
    }
    const invalid = phones.filter((p) => !PHONE_RE.test(p));
    if (invalid.length > 0) {
      notify({
        type: 'error',
        title: 'Invalid phone number',
        message: `Use international format, e.g. +254712345678: ${invalid.join(', ')}`,
      });
      return;
    }

    setSending(true);
    try {
      let token = null;
      try {
        const supabase = await getSupabase();
        const { data } = await supabase.auth.getSession();
        token = data?.session?.access_token;
      } catch {
        // Guest — send without a token.
      }
      const res = await sendHazardAlert({
        hazard,
        location,
        role,
        language,
        phoneNumbers: phones,
        token,
      });
      notify({
        type: res.success ? 'success' : 'error',
        title: res.success ? 'Alert queued' : 'Not sent',
        message: res.message,
      });
      fetchAlertHistory().then(setHistory).catch(() => {});
    } catch (e) {
      notify({ type: 'error', title: 'Send failed', message: e.message });
    } finally {
      setSending(false);
    }
  }

  if (authLoading) {
    return <div className="loading-container" style={{ minHeight: '60vh' }} />;
  }

  const languages = profile?.languages?.length ? profile.languages : ['en'];
  const selectedMeta = hazard ? hazardMeta(hazard) : null;
  const canSend = Boolean(hazard && location && relevant && !previewLoading && preview);

  return (
    <div className="page-container">
      <div
        className="page-header"
        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}
      >
        <div>
          <h1 className="page-title">Alerts</h1>
          <p className="page-description">
            Send a plain-language advisory to a phone, for any hazard, anywhere. Pick the hazard,
            then the place.
          </p>
        </div>
        {user ? (
          <button className="btn" onClick={logout}>Logout</button>
        ) : (
          <button className="btn" onClick={() => setShowAuthModal(true)}>Sign in</button>
        )}
      </div>

      <div className="grid-2col">
        <div className="card">
          <div className="card-header">
            <div className="card-title">1 · Choose a hazard</div>
          </div>

          <div className="hazard-chooser">
            {catalog.map((h) => {
              const meta = hazardMeta(h.hazard);
              return (
                <button
                  key={h.hazard}
                  type="button"
                  className={`hazard-chip ${hazard === h.hazard ? 'active' : ''}`}
                  onClick={() => setHazard(h.hazard)}
                  aria-pressed={hazard === h.hazard}
                >
                  <span aria-hidden="true">{meta.icon}</span> {meta.short}
                </button>
              );
            })}
          </div>

          <div className="card-header" style={{ marginTop: 20 }}>
            <div className="card-title">2 · Choose a place</div>
          </div>
          <LocationBar location={location} onSelect={setLocation} busy={profileLoading} />

          {location && profile && !profileLoading && !relevant && (
            <div className="notice notice--warn" role="status" style={{ marginTop: 10 }}>
              {selectedMeta?.label} is not a relevant hazard at {placeLabel(location)} — Tayari
              found no physical basis for it there, so there is nothing to warn about. Choose a
              different hazard or place.
            </div>
          )}

          <div className="card-header" style={{ marginTop: 20 }}>
            <div className="card-title">3 · Who it is for</div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="alert-role">Audience</label>
            <select
              id="alert-role"
              className="form-select"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
          </div>

          {languages.length > 1 && (
            <div className="form-group">
              <label className="form-label">Language</label>
              <div className="lang-selector">
                {languages.map((code) => (
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

          <div className="form-group">
            <label className="form-label" htmlFor="phones">Phone number(s)</label>
            <input
              id="phones"
              className="form-input"
              type="text"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="+254712345678, +252612345678"
            />
            <p className="form-hint">
              International format. Separate several with commas. Each number can receive one
              alert every five minutes.
            </p>
          </div>

          <button
            className="btn btn-primary btn-lg"
            onClick={handleSend}
            disabled={sending || !canSend}
            style={{ width: '100%', marginTop: 4 }}
          >
            {sending ? 'Sending…' : 'Send advisory'}
          </button>
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">What they will receive</div>
            {previewLoading && <span className="card-subtitle">Writing…</span>}
          </div>

          <div className={`sms-preview ${previewError ? 'sms-preview--error' : ''}`}>
            {previewLoading ? (
              <div className="spinner" />
            ) : previewError ? (
              previewError
            ) : preview ? (
              preview
            ) : (
              'Choose a hazard and a place to see the exact message that will be sent.'
            )}
          </div>

          {preview && (
            <p className="form-hint" style={{ marginTop: 10 }}>
              {preview.length} characters — about {Math.ceil(preview.length / 153)} SMS parts.
            </p>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-header">
          <div className="card-title">Alert history</div>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{history.length} sent</span>
        </div>
        {history.length === 0 ? (
          <div className="empty-state">No alerts sent yet.</div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Subject</th>
                  <th>Risk</th>
                  <th>Audience</th>
                  <th>Language</th>
                  <th>Recipients</th>
                  <th>Sent at</th>
                </tr>
              </thead>
              <tbody>
                {history.slice().reverse().map((alert) => (
                  <tr key={alert.id}>
                    <td>{formatSubject(alert.basin_id)}</td>
                    <td>
                      <span className={`risk-badge risk-badge--${alert.risk_level?.toLowerCase()}`}>
                        {alert.risk_level}
                      </span>
                    </td>
                    <td>{alert.role}</td>
                    <td>{alert.language}</td>
                    <td>{alert.recipients_count}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                      {new Date(alert.sent_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showAuthModal && <AuthModal onClose={() => setShowAuthModal(false)} />}
    </div>
  );
}

/**
 * Render an alert's subject key.
 *
 * History rows carry either a basin id (`shabelle`) or a hazard-and-place key
 * (`extreme_heat@-33.87,151.21`), because the two alert paths share one column.
 */
function formatSubject(subject) {
  if (!subject) return '—';
  if (!subject.includes('@')) return subject;
  const [hazard, coords] = subject.split('@');
  return `${hazardMeta(hazard).short} · ${coords}`;
}
