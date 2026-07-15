'use client';

import { useState, useEffect } from 'react';
import { sendAlert, fetchAlertHistory, fetchAdvisory } from '@/lib/api';
import { BASINS, ROLES, LANGUAGES } from '@/lib/constants';
import { useToast } from '@/components/Toast';

export default function AlertsPage() {
  const [basinId, setBasinId] = useState('shabelle');
  const [role, setRole] = useState('farmer');
  const [language, setLanguage] = useState('en');
  const [phoneNumber, setPhoneNumber] = useState('+2521234567');
  const [smsPreview, setSmsPreview] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(false);
  const [sending, setSending] = useState(false);
  const [history, setHistory] = useState([]);

  const { notify } = useToast();

  // Refresh the SMS preview whenever the targeting changes
  useEffect(() => {
    loadPreview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [basinId, role, language]);

  useEffect(() => {
    loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadPreview() {
    setPreviewLoading(true);
    setPreviewError(false);
    try {
      const data = await fetchAdvisory(basinId, role, language);
      setSmsPreview(data.sms_text || '');
    } catch (err) {
      console.error('Failed to load preview:', err);
      setPreviewError(true);
      setSmsPreview('Could not generate a preview. Is the backend running on port 8000?');
    } finally {
      setPreviewLoading(false);
    }
  }

  async function loadHistory() {
    try {
      const data = await fetchAlertHistory();
      setHistory(data);
    } catch (err) {
      console.error('Failed to load history:', err);
    }
  }

  function parsePhones(raw) {
    return raw
      .split(',')
      .map((p) => p.trim())
      .filter(Boolean);
  }

  async function handleSend() {
    const phones = parsePhones(phoneNumber);
    if (phones.length === 0) {
      notify({
        type: 'error',
        title: 'No recipients',
        message: 'Enter at least one phone number in international format (e.g. +2521234567).',
      });
      return;
    }
    const invalid = phones.filter((p) => !/^\+?\d{7,15}$/.test(p));
    if (invalid.length > 0) {
      notify({
        type: 'error',
        title: 'Check the phone numbers',
        message: `These don't look valid: ${invalid.join(', ')}`,
      });
      return;
    }

    setSending(true);
    try {
      const res = await sendAlert(basinId, role, language, phones);
      if (res.success) {
        notify({
          type: 'success',
          title: 'Alert sent',
          message: res.message || `Sent to ${phones.length} recipient(s).`,
        });
      } else {
        notify({ type: 'error', title: 'Send failed', message: res.message });
      }
      loadHistory();
    } catch (err) {
      notify({ type: 'error', title: 'Send failed', message: err.message });
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Alerts</h1>
        <p className="page-description">
          Generate and send multilingual flood advisories via SMS. Messages go out through
          Africa&apos;s Talking (sandbox mode for the demo).
        </p>
      </div>

      <div style={{ display: 'grid', gap: '20px', gridTemplateColumns: '1fr 1fr' }}>
        <div className="card">
          <div className="card-header">
            <div className="card-title">Send an alert</div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div className="form-group">
              <label className="form-label" htmlFor="basin">Basin</label>
              <select
                id="basin"
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
              <label className="form-label" htmlFor="target-role">Audience</label>
              <select
                id="target-role"
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

            <div className="form-group">
              <label className="form-label">Language</label>
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

            <div className="form-group">
              <label className="form-label" htmlFor="phones">Phone number(s)</label>
              <input
                id="phones"
                className="form-input"
                type="text"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                placeholder="+2521234567"
              />
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Separate multiple numbers with commas.
              </span>
            </div>

            <button
              className="btn btn-primary btn-lg"
              onClick={handleSend}
              disabled={sending || previewLoading}
              style={{ marginTop: '4px' }}
            >
              {sending ? (
                <>
                  <span className="spinner" style={{ width: 15, height: 15 }} />
                  Sending…
                </>
              ) : (
                'Send SMS alert'
              )}
            </button>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">SMS preview</div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              {smsPreview.length} chars
            </span>
          </div>
          <div
            style={{
              background: 'var(--surface-sunken)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-sm)',
              padding: '14px',
              fontFamily: 'var(--font-mono)',
              fontSize: '13px',
              lineHeight: '1.65',
              color: previewError ? 'var(--risk-high)' : 'var(--text-secondary)',
              minHeight: '200px',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {previewLoading ? (
              <div className="loading-container" style={{ padding: '20px' }}>
                <div className="spinner" />
              </div>
            ) : (
              smsPreview
            )}
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: '20px' }}>
        <div className="card-header">
          <div className="card-title">Alert history</div>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            {history.length} sent
          </span>
        </div>
        {history.length === 0 ? (
          <div className="empty-state">No alerts sent yet. Send your first one above.</div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Basin</th>
                  <th>Risk</th>
                  <th>Audience</th>
                  <th>Language</th>
                  <th>Recipients</th>
                  <th>Sent at</th>
                </tr>
              </thead>
              <tbody>
                {history
                  .slice()
                  .reverse()
                  .map((alert) => (
                    <tr key={alert.id}>
                      <td>{alert.basin_id}</td>
                      <td>
                        <span
                          className={`risk-badge risk-badge--${alert.risk_level?.toLowerCase()}`}
                        >
                          {alert.risk_level}
                        </span>
                      </td>
                      <td>{alert.role}</td>
                      <td>{alert.language}</td>
                      <td>{alert.recipients_count}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                        {new Date(alert.sent_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
