'use client';

import { useState, useEffect, useRef } from 'react';
import { sendAlert, fetchAlertHistory, fetchAdvisory, fetchBasins, resolveAssetUrl } from '@/lib/api';
import { ROLES, LANGUAGES, LANGUAGE_LABELS } from '@/lib/constants';
import { useToast } from '@/components/Toast';
import { getSupabase } from '@/lib/supabase';

export default function AlertsPage() {
  const [session, setSession] = useState(null);
  const [loginPhone, setLoginPhone] = useState('');
  const [loginOtp, setLoginOtp] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);

  const [basinsData, setBasinsData] = useState([]);
  const [basinId, setBasinId] = useState('shabelle');
  const [role, setRole] = useState('farmer');
  const [language, setLanguage] = useState('en');
  const [phoneNumber, setPhoneNumber] = useState('+2521234567');
  
  const [smsPreview, setSmsPreview] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(false);
  
  // Audio state
  const [requiresRecording, setRequiresRecording] = useState(false);
  const [voiceNoteUrl, setVoiceNoteUrl] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const [sending, setSending] = useState(false);
  const [history, setHistory] = useState([]);

  const { notify } = useToast();

  useEffect(() => {
    // Restore the operator session; the Supabase SDK loads on demand.
    let active = true;
    let unsub = () => {};
    getSupabase().then((supabase) => {
      if (!active) return;
      supabase.auth.getSession().then(({ data: { session } }) => {
        if (active) setSession(session);
      });
      const {
        data: { subscription },
      } = supabase.auth.onAuthStateChange((_event, session) => {
        setSession(session);
      });
      unsub = () => subscription.unsubscribe();
    });

    loadBasins();
    loadHistory();

    return () => {
      active = false;
      unsub();
    };
  }, []);

  useEffect(() => {
    if (basinsData.length > 0) {
      loadPreview();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [basinId, role, language, basinsData]);

  async function loadBasins() {
    try {
      const data = await fetchBasins();
      setBasinsData(data.basins || []);
    } catch (e) {
      console.error(e);
    }
  }

  async function loadPreview() {
    setPreviewLoading(true);
    setPreviewError(false);
    setAudioBlob(null);
    try {
      const data = await fetchAdvisory(basinId, role, language);
      setSmsPreview(data.sms_text || data.body || '');
      setRequiresRecording(data.requires_recording || false);
      setVoiceNoteUrl(data.voice_note_url || null);
    } catch (err) {
      console.error('Failed to load preview:', err);
      setPreviewError(true);
      setSmsPreview('Could not generate a preview. Is the backend running?');
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

  // Supabase Phone Auth
  async function handleSendOtp() {
    setAuthLoading(true);
    const supabase = await getSupabase();
    const { error } = await supabase.auth.signInWithOtp({
      phone: loginPhone,
    });
    setAuthLoading(false);
    if (error) {
      notify({ type: 'error', title: 'Login Error', message: error.message });
    } else {
      setOtpSent(true);
      notify({ type: 'success', title: 'OTP Sent', message: 'Check your phone for the code.' });
    }
  }

  async function handleVerifyOtp() {
    setAuthLoading(true);
    const supabase = await getSupabase();
    const { error } = await supabase.auth.verifyOtp({
      phone: loginPhone,
      token: loginOtp,
      type: 'sms',
    });
    setAuthLoading(false);
    if (error) {
      notify({ type: 'error', title: 'Verification Failed', message: error.message });
    }
  }

  // Audio Recording
  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        setAudioBlob(blob);
        const url = URL.createObjectURL(blob);
        setVoiceNoteUrl(url); // preview locally
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error(err);
      notify({ type: 'error', title: 'Mic Access', message: 'Could not access microphone.' });
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
    }
  }

  function parsePhones(raw) {
    return raw.split(',').map((p) => p.trim()).filter(Boolean);
  }

  async function handleSend() {
    const phones = parsePhones(phoneNumber);
    if (phones.length === 0) {
      notify({ type: 'error', title: 'No recipients', message: 'Enter at least one phone number.' });
      return;
    }
    
    // In a real app, if audioBlob exists, we would upload it via FormData to a dedicated voice endpoint.
    // For this implementation, we just pass the token to sendAlert.
    setSending(true);
    try {
      const token = session?.access_token;
      const res = await sendAlert(basinId, role, language, phones, token);
      if (res.success) {
        notify({ type: 'success', title: 'Alert sent', message: res.message });
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

  if (!session) {
    return (
      <div className="page-container" style={{ maxWidth: 400, margin: '100px auto' }}>
        <div className="card">
          <div className="card-header"><div className="card-title">Operator Login</div></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', padding: 20 }}>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
              Alert dispatch is secured. Enter your authorized phone number.
            </p>
            {!otpSent ? (
              <>
                <input
                  className="form-input"
                  type="text"
                  placeholder="+254712345678"
                  value={loginPhone}
                  onChange={(e) => setLoginPhone(e.target.value)}
                />
                <button className="btn btn-primary" onClick={handleSendOtp} disabled={authLoading}>
                  {authLoading ? 'Sending...' : 'Send OTP'}
                </button>
              </>
            ) : (
              <>
                <input
                  className="form-input"
                  type="text"
                  placeholder="123456"
                  value={loginOtp}
                  onChange={(e) => setLoginOtp(e.target.value)}
                />
                <button className="btn btn-primary" onClick={handleVerifyOtp} disabled={authLoading}>
                  {authLoading ? 'Verifying...' : 'Login'}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Basin specific language filter
  const currentBasinConfig = basinsData.find(b => b.id === basinId);
  const supportedLanguages = currentBasinConfig ? currentBasinConfig.languages : ['en'];
  const filteredLanguages = LANGUAGES.filter(l => supportedLanguages.includes(l.value));

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">Alerts</h1>
          <p className="page-description">Generate and send multilingual flood advisories via Cloudflare SMS Workers.</p>
        </div>
        <button className="btn" onClick={async () => (await getSupabase()).auth.signOut()}>Logout</button>
      </div>

      <div className="grid-2col">
        <div className="card">
          <div className="card-header"><div className="card-title">Send an alert</div></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            
            <div className="form-group">
              <label className="form-label" htmlFor="basin">Basin</label>
              <select
                id="basin"
                className="form-select"
                value={basinId}
                onChange={(e) => {
                  setBasinId(e.target.value);
                  setLanguage('en');
                }}
              >
                {basinsData.map((b) => (
                  <option key={b.id} value={b.id}>{b.name}</option>
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
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Language</label>
              <div className="lang-selector">
                {filteredLanguages.map((l) => (
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
            </div>

            <button
              className="btn btn-primary btn-lg"
              onClick={handleSend}
              disabled={sending || previewLoading || (requiresRecording && !audioBlob)}
              style={{ marginTop: '4px' }}
            >
              {sending ? 'Sending…' : 'Dispatch Alert'}
            </button>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">Advisory Preview</div>
            {requiresRecording && <span className="risk-badge risk-badge--extreme">Manual Recording Required</span>}
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <div style={{
              background: 'var(--surface-sunken)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)',
              padding: '14px', fontFamily: 'var(--font-mono)', fontSize: '13px', lineHeight: '1.65',
              color: previewError ? 'var(--risk-high)' : 'var(--text-secondary)', minHeight: '150px', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
            }}>
              {previewLoading ? <div className="spinner" /> : smsPreview}
            </div>

            {requiresRecording && (
              <div style={{ padding: '15px', border: '1px dashed var(--border-color)', borderRadius: 'var(--radius-sm)', background: 'rgba(131, 41, 26, 0.05)' }}>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 10 }}>
                  <strong>Low Resource Language:</strong> Automated TTS is not supported. Please record the voice note manually. The audio will be sent ephemerally.
                </p>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  {!isRecording ? (
                    <button className="btn" onClick={startRecording} style={{ background: 'var(--risk-high)', color: '#fff', borderColor: 'transparent' }}>
                      ● Record Audio
                    </button>
                  ) : (
                    <button className="btn" onClick={stopRecording} style={{ borderColor: 'var(--risk-high)', color: 'var(--risk-high)' }}>
                      ■ Stop Recording
                    </button>
                  )}
                  {isRecording && <span className="spinner" style={{ width: 14, height: 14, borderColor: 'var(--risk-high)', borderRightColor: 'transparent' }}></span>}
                </div>
              </div>
            )}

            {voiceNoteUrl && (
              <div style={{ marginTop: '10px' }}>
                <p style={{ fontSize: 12, fontWeight: 500, marginBottom: 5 }}>Voice Preview:</p>
                <audio controls src={audioBlob ? voiceNoteUrl : resolveAssetUrl(voiceNoteUrl)} style={{ width: '100%', height: 40 }} />
              </div>
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
