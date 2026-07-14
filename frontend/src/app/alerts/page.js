'use client';

import { useState, useEffect } from 'react';
import { sendAlert, fetchAlertHistory, fetchAdvisory } from '@/lib/api';
import { BASINS, ROLES, LANGUAGES, RISK_COLORS } from '@/lib/constants';

export default function AlertsPage() {
  const [basinId, setBasinId] = useState('shabelle');
  const [role, setRole] = useState('farmer');
  const [language, setLanguage] = useState('en');
  const [phoneNumber, setPhoneNumber] = useState('+2521234567');
  const [smsPreview, setSmsPreview] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);

  // Load preview when settings change
  useEffect(() => {
    loadPreview();
  }, [basinId, role, language]);

  // Load alert history on mount
  useEffect(() => {
    loadHistory();
  }, []);

  async function loadPreview() {
    setPreviewLoading(true);
    try {
      const data = await fetchAdvisory(basinId, role, language);
      setSmsPreview(data.sms_text || '');
    } catch (err) {
      console.error('Failed to load preview:', err);
      setSmsPreview('Failed to generate preview. Is the backend running?');
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

  async function handleSend() {
    setSending(true);
    setResult(null);
    try {
      const phones = phoneNumber
        .split(',')
        .map((p) => p.trim())
        .filter(Boolean);
      const res = await sendAlert(basinId, role, language, phones);
      setResult(res);
      loadHistory(); // Refresh history
    } catch (err) {
      setResult({ success: false, message: err.message });
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">📡 Alert Management</h1>
        <p className="page-description">
          Generate and send multilingual flood advisories via SMS. Alerts are
          sent through Africa's Talking (sandbox mode for demo).
        </p>
      </div>

      <div style={{ display: 'grid', gap: '24px', gridTemplateColumns: '1fr 1fr' }}>
        {/* Send Alert */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Send Alert</div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
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
              <label className="form-label">Target Role</label>
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

            <div className="form-group">
              <label className="form-label">Language</label>
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

            <div className="form-group">
              <label className="form-label">Phone Number(s)</label>
              <input
                className="form-input"
                type="text"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                placeholder="+2521234567"
              />
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Separate multiple numbers with commas
              </span>
            </div>

            <button
              className="btn btn-primary btn-lg"
              onClick={handleSend}
              disabled={sending}
              style={{ marginTop: '8px' }}
            >
              {sending ? (
                <>
                  <span className="spinner" style={{ width: 16, height: 16 }} />
                  Sending...
                </>
              ) : (
                '📤 Send SMS Alert'
              )}
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
                  {result.success ? '✅ Alert Sent' : '❌ Failed'}
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  {result.message}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* SMS Preview */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">📱 SMS Preview</div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              {smsPreview.length} chars
            </span>
          </div>
          <div
            style={{
              background: 'var(--bg-primary)',
              borderRadius: '12px',
              padding: '16px',
              fontFamily: 'var(--font-mono)',
              fontSize: '13px',
              lineHeight: '1.7',
              color: 'var(--text-secondary)',
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

      {/* Alert History */}
      <div className="card" style={{ marginTop: '24px' }}>
        <div className="card-header">
          <div className="card-title">📋 Alert History</div>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            {history.length} alerts sent
          </span>
        </div>
        {history.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '14px', textAlign: 'center', padding: '20px' }}>
            No alerts sent yet. Send your first alert above.
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Basin</th>
                  <th>Risk</th>
                  <th>Role</th>
                  <th>Language</th>
                  <th>Recipients</th>
                  <th>Sent At</th>
                </tr>
              </thead>
              <tbody>
                {history.map((alert) => (
                  <tr key={alert.id}>
                    <td>{alert.basin_id}</td>
                    <td>
                      <span className={`risk-badge risk-badge--${alert.risk_level?.toLowerCase()}`}>
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
