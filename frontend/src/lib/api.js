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
 * Submit user feedback to the system.
 */
export async function sendFeedback(rating, subject, comment) {
  const res = await fetch(`${API_BASE}/api/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rating, subject, comment }),
  });
  if (!res.ok) throw new Error(`Failed to submit feedback: ${res.status}`);
  return res.json();
}
