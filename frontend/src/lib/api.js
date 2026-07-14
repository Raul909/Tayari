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
export async function sendAlert(basinId, role, language, phoneNumbers) {
  const res = await fetch(`${API_BASE}/api/alerts/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
