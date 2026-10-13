/**
 * How the web app reaches the API.
 *
 * In production the API is called on this site's own origin: `/api/*` is served
 * by the edge gateway (edge/gateway.js), which caches answers at Cloudflare and
 * keeps serving recent ones while the free Render instance sleeps. Same-origin
 * also means no CORS preflight, which is a whole extra round trip per POST on a
 * slow mobile network.
 *
 * The gateway must never become the reason Tayari is down, though. It runs on
 * Cloudflare's free plan, which has a daily request allowance; past it, or in
 * any other failure of the gateway itself, `apiFetch` goes straight to Render
 * instead. A failure *of Render* reported by the gateway (it marks those with
 * an `x-tayari-edge` header) is not retried, because Render is down either way.
 *
 * In development NEXT_PUBLIC_API_URL points at the local backend and the
 * fallback never applies.
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// The API's own address, used only when the gateway in front of it fails.
const DIRECT_ORIGIN = 'https://tayari-api.onrender.com';

function gatewayFailed(response) {
  return response.status >= 429 && !response.headers.has('x-tayari-edge');
}

/** fetch() for API paths ("/api/..."), with a direct-to-origin fallback. */
export async function apiFetch(path, init) {
  if (API_BASE !== '') return fetch(`${API_BASE}${path}`, init);
  try {
    const response = await fetch(path, init);
    if (!gatewayFailed(response)) return response;
  } catch (error) {
    if (error?.name === 'AbortError') throw error;
  }
  return fetch(`${DIRECT_ORIGIN}${path}`, init);
}

/** Absolute URL for a file the API serves (report photos, voice notes). */
export function assetUrl(path) {
  if (!path) return null;
  return path.startsWith('http') ? path : `${API_BASE}${path}`;
}
