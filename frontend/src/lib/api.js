/**
 * Backend API client for Tayari.
 */

import { apiFetch, assetUrl } from '@/lib/http';

/**
 * Fetch all basins with current risk levels.
 */
export async function fetchBasins() {
  const res = await apiFetch(`/api/basins`);
  if (!res.ok) throw new Error(`Failed to fetch basins: ${res.status}`);
  return res.json();
}

/**
 * Fetch full forecast for a basin.
 */
export async function fetchForecast(basinId, role = 'general', language = 'en') {
  const res = await apiFetch(`/api/forecasts/${basinId}?role=${role}&language=${language}`
  );
  if (!res.ok) throw new Error(`Failed to fetch forecast: ${res.status}`);
  return res.json();
}

/**
 * Fetch historical discharge for hindcast.
 */
export async function fetchHistory(basinId, startDate, endDate) {
  const res = await apiFetch(`/api/forecasts/${basinId}/history?start_date=${startDate}&end_date=${endDate}`
  );
  if (!res.ok) throw new Error(`Failed to fetch history: ${res.status}`);
  return res.json();
}

/**
 * Fetch advisory in a specific role and language.
 */
export async function fetchAdvisory(basinId, role = 'general', language = 'en') {
  const res = await apiFetch(`/api/advisory/${basinId}?role=${role}&language=${language}`
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
  const res = await apiFetch(`/api/alerts/send`, {
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
    ? `/api/alerts/history?basin_id=${basinId}`
    : `/api/alerts/history`;
  const res = await apiFetch(url);
  if (!res.ok) throw new Error(`Failed to fetch alert history: ${res.status}`);
  return res.json();
}

/**
 * Submit a community report.
 */
export async function submitReport(report) {
  const res = await apiFetch(`/api/reports`, {
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

  const res = await apiFetch(`/api/reports/upload`, {
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
  const res = await apiFetch(`/api/reports/${reportId}/advice`, {
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
    ? `/api/reports?basin_id=${basinId}`
    : `/api/reports`;
  const res = await apiFetch(url);
  if (!res.ok) throw new Error(`Failed to fetch reports: ${res.status}`);
  return res.json();
}

/**
 * Resolve a backend-relative asset path (e.g. /uploads/…) to a full URL.
 */
export function resolveAssetUrl(path) {
  return assetUrl(path);
}

/**
 * Send a chat message about an advisory.
 */
export async function sendChatMessage(basinId, message, role = 'general', language = 'en', sessionMessages = [], userId = null) {
  const res = await apiFetch(`/api/chat/${basinId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, role, language, session_messages: sessionMessages, user_id: userId }),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
  return res.json();
}

export const RATING_LABELS = { 1: 'Very poor', 2: 'Poor', 3: 'Okay', 4: 'Good', 5: 'Very good' };

// FormSubmit's alias for the feedback inbox, issued
// when the form was activated for tayari.pages.dev. Using it instead of the
// address keeps the inbox out of this public bundle. Same alias as the backend,
// the lite pages and the phone app.
const FORMSUBMIT_ENDPOINT = 'https://formsubmit.co/ajax/bc7b96d4113e366589fd2e528232a340';

/**
 * Deliver a feedback email directly to the feedback inbox via FormSubmit.co.
 * Returns true only when FormSubmit confirms delivery.
 *
 * The browser is the reliable place to do this: it attaches the Origin header
 * FormSubmit requires (JS can't set it), and — unlike the Render backend, whose
 * datacenter IP FormSubmit blocks — a real browser can actually reach it.
 * FormSubmit reports failures in the JSON body, not the HTTP status (an
 * unactivated/rejected form returns 200 with {"success":"false"}), so we check
 * the body rather than trusting the 200.
 */
async function deliverFeedbackViaFormSubmit(rating, subject, comment) {
  const ratingText = RATING_LABELS[rating] ? `${rating}/5 – ${RATING_LABELS[rating]}` : String(rating);
  const subjectText = subject || 'General';
  const payload = {
    rating: ratingText,
    subject: subjectText,
    message: `New Feedback Received!\n\nOpinion Rating: ${ratingText}\nSubject: ${subjectText}\n\nComment:\n${comment || 'No comment provided.'}`,
    _subject: `Tayari Feedback - ${subjectText} (${ratingText})`,
  };

  const res = await fetch(FORMSUBMIT_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) return false;
  const body = await res.json().catch(() => ({}));
  return String(body.success).toLowerCase() === 'true';
}

/**
 * Submit user feedback.
 *
 * The email goes straight from the browser to FormSubmit.co — the reliable path
 * (see deliverFeedbackViaFormSubmit). The backend is then told about it, so the
 * feedback is also recorded for analytics; `email_sent` stops the backend from
 * sending the same email a second time. That call is fire-and-forget: a cold
 * start or a database outage must never fail a submission that was delivered.
 */
export async function sendFeedback(rating, subject, comment) {
  const delivered = await deliverFeedbackViaFormSubmit(rating, subject, comment).catch(() => false);
  const record = (emailSent) =>
    apiFetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rating, subject, comment, email_sent: emailSent }),
    });

  if (delivered) {
    record(true).catch(() => {});
    return { success: true, message: 'Feedback sent' };
  }

  // FormSubmit did not take it: let the backend try to send it, which also
  // stores it, so a FormSubmit outage loses nothing.
  const res = await record(false).catch(() => null);
  if (!res?.ok) {
    throw new Error('Could not deliver feedback. Please try again later.');
  }
  return { success: true, message: 'Feedback sent' };
}
