/**
 * Backend API client for Tayari.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Fetch all basins with current risk levels.
 */
export async function fetchBasins() {
  const res = await fetch(`${API_BASE}/api/basins`);
  if (!res.ok) throw new Error(`Failed to fetch basins: ${res.status}`);
  return res.json();
}

/**
 * Fetch full forecast for a basin.
 */
export async function fetchForecast(basinId, role = 'general', language = 'en') {
  const res = await fetch(
    `${API_BASE}/api/forecasts/${basinId}?role=${role}&language=${language}`
  );
  if (!res.ok) throw new Error(`Failed to fetch forecast: ${res.status}`);
  return res.json();
}

/**
 * Fetch historical discharge for hindcast.
 */
export async function fetchHistory(basinId, startDate, endDate) {
  const res = await fetch(
    `${API_BASE}/api/forecasts/${basinId}/history?start_date=${startDate}&end_date=${endDate}`
  );
  if (!res.ok) throw new Error(`Failed to fetch history: ${res.status}`);
  return res.json();
}

/**
 * Fetch advisory in a specific role and language.
 */
export async function fetchAdvisory(basinId, role = 'general', language = 'en') {
  const res = await fetch(
    `${API_BASE}/api/advisory/${basinId}?role=${role}&language=${language}`
  );
  if (!res.ok) throw new Error(`Failed to fetch advisory: ${res.status}`);
  return res.json();
}

/**
 * Send an SMS alert.
 */
export async function sendAlert(basinId, role, language, phoneNumbers, token) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE}/api/alerts/send`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      basin_id: basinId,
      role,
      language,
      phone_numbers: phoneNumbers,
    }),
  });
  if (!res.ok) throw new Error(`Failed to send alert: ${res.status}`);
  return res.json();
}

/**
 * Get alert history.
 */
export async function fetchAlertHistory(basinId = null) {
  const url = basinId
    ? `${API_BASE}/api/alerts/history?basin_id=${basinId}`
    : `${API_BASE}/api/alerts/history`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch alert history: ${res.status}`);
  return res.json();
}

/**
 * Submit a community report.
 */
export async function submitReport(report) {
  const res = await fetch(`${API_BASE}/api/reports`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(report),
  });
  if (!res.ok) throw new Error(`Failed to submit report: ${res.status}`);
  return res.json();
}

/**
 * Submit a community report with a photo as multipart/form-data.
 */
export async function submitReportWithPhoto(fields, photoFile) {
  const formData = new FormData();
  Object.entries(fields).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      formData.append(key, value);
    }
  });
  if (photoFile) formData.append('photo', photoFile);

  const res = await fetch(`${API_BASE}/api/reports/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`Failed to submit report: ${res.status}`);
  return res.json();
}

/**
 * Attach advice/guidance to a community report.
 */
export async function submitAdvice(reportId, advice) {
  const res = await fetch(`${API_BASE}/api/reports/${reportId}/advice`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(advice),
  });
  if (!res.ok) throw new Error(`Failed to submit advice: ${res.status}`);
  return res.json();
}

/**
 * Get community reports.
 */
export async function fetchReports(basinId = null) {
  const url = basinId
    ? `${API_BASE}/api/reports?basin_id=${basinId}`
    : `${API_BASE}/api/reports`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch reports: ${res.status}`);
  return res.json();
}

/**
 * Resolve a backend-relative asset path (e.g. /uploads/…) to a full URL.
 */
export function resolveAssetUrl(path) {
  if (!path) return null;
  return path.startsWith('http') ? path : `${API_BASE}${path}`;
}

/**
 * Send a chat message about an advisory.
 */
export async function sendChatMessage(basinId, message, role = 'general', language = 'en', sessionMessages = [], userId = null) {
  const res = await fetch(`${API_BASE}/api/chat/${basinId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, role, language, session_messages: sessionMessages, user_id: userId }),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
  return res.json();
}

/**
 * Submit user feedback.
 *
 * Primary path: POST to the backend, which emails contact@launchpixel.in via
 * FormSubmit.co *and* saves to the database.
 *
 * Fallback: if the backend is unreachable (Render cold-start, DB down, etc.),
 * send directly to FormSubmit.co from the browser so feedback is never lost.
 */
const RATING_LABELS = { 1: 'Angry 😠', 2: 'Sad 😞', 3: 'Neutral 😐', 4: 'Happy 🙂', 5: 'Very Happy 😄' };

export async function sendFeedback(rating, subject, comment) {
  // --- Try backend first ---
  try {
    const res = await fetch(`${API_BASE}/api/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rating, subject, comment }),
    });
    if (res.ok) return res.json();
    // 4xx errors (e.g. bad rating) should surface immediately, don't fallback.
    if (res.status >= 400 && res.status < 500) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Feedback rejected: ${res.status}`);
    }
    // 5xx → fall through to FormSubmit.co fallback
  } catch (err) {
    // Network error or 5xx — fall through to direct delivery
    if (err.message && !err.message.includes('Feedback rejected')) {
      console.warn('Backend feedback failed, using FormSubmit.co fallback:', err.message);
    } else {
      throw err; // re-throw 4xx errors
    }
  }

  // --- Fallback: send directly to FormSubmit.co ---
  const ratingText = RATING_LABELS[rating] || String(rating);
  const subjectText = subject || 'General';
  const payload = {
    rating: ratingText,
    subject: subjectText,
    message: `New Feedback Received!\n\nOpinion Rating: ${ratingText}\nSubject: ${subjectText}\n\nComment:\n${comment || 'No comment provided.'}`,
    _subject: `Tayari Feedback - ${subjectText} (${ratingText})`,
  };

  const res = await fetch('https://formsubmit.co/ajax/contact@launchpixel.in', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Could not deliver feedback. Please try again later.');
  // FormSubmit reports real failures in the body, not the HTTP status: an
  // unactivated form or a rejected request returns 200 with {"success":"false"}.
  // The browser attaches the Origin header automatically, so an activated form
  // succeeds here — but verify rather than trust the 200.
  const body = await res.json().catch(() => ({}));
  if (String(body.success).toLowerCase() !== 'true') {
    throw new Error('Could not deliver feedback. Please try again later.');
  }
  return { success: true, message: 'Feedback sent (direct delivery)' };
}
