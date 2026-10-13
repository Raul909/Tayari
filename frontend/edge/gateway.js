/**
 * Tayari's edge gateway: the API, served from Cloudflare in front of Render.
 *
 * Everything Tayari runs on is a free tier, and the weakest link is the API: one
 * Render instance with a tenth of a CPU that falls asleep after fifteen idle
 * minutes and takes most of a minute to wake. Traffic to a warning service is
 * the opposite of even — it arrives all at once, from one place, when something
 * happens there. So the gateway's job is to make sure most requests never reach
 * Render at all, and that the ones that must can survive it being slow or asleep.
 *
 *   fresh   inside s-maxage: answered from the edge, Render never hears of it.
 *   stale   inside stale-while-revalidate: answered from the edge at once, and
 *           refreshed in the background so the next reader gets new data.
 *   error   Render is down, asleep or slower than STALE_WAIT_MS, and we hold a
 *           copy inside stale-if-error: that copy is served, marked as stale.
 *
 * Render decides every route's lifetimes in its Cache-Control header
 * (backend/app/main.py `_CACHE_POLICY`); the gateway only obeys them, so the rule
 * for how fresh an answer must be lives next to the code that knows. Anything
 * not marked `public` — accounts, alert history — passes straight through.
 *
 * Being on the same origin as the web app has a second payoff on bad networks:
 * no CORS preflight, so a POST costs one round trip instead of two, and browsers
 * too old to speak CORS can still use the API.
 */

// Render, unless the API_ORIGIN binding points elsewhere (local testing).
export const DEFAULT_ORIGIN = 'https://tayari-api.onrender.com';

// How long to wait for Render when a stale copy is on hand. Long enough for a
// warm instance on a slow upstream, far shorter than a cold start.
const STALE_WAIT_MS = 6000;
// How long to wait when there is nothing to fall back on. A cold start takes
// 30-50 s, and waiting is better than failing.
const COLD_WAIT_MS = 60000;

// Report writes that change the shared report list.
const REPORT_WRITE = /^\/api\/reports(\/|$)/;

/** Rewrite a request URL into its cache key, so equivalent requests share one entry. */
function normalise(url) {
  const params = [...url.searchParams.entries()].filter(([, v]) => v !== '');
  const isHazard = url.pathname === '/api/hazards' || /^\/api\/hazards\/[a-z_]+\/advisory$/.test(url.pathname);
  const out = new URLSearchParams();
  params
    .map(([k, v]) => {
      // Coordinates to 4 decimals (~11 m) — the precision the API itself keys
      // its caches on. A GPS fix and a search result for the same street then
      // share one entry instead of each costing a full assessment.
      if (isHazard && (k === 'lat' || k === 'lon')) {
        const n = Number(v);
        return [k, Number.isFinite(n) ? n.toFixed(4) : v];
      }
      if (k === 'country_code') return [k, v.toLowerCase()];
      return [k, v];
    })
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .forEach(([k, v]) => out.append(k, v));
  const query = out.toString();
  return url.pathname + (query ? `?${query}` : '');
}

/** Parse the directives we act on out of a Cache-Control header. */
function policyOf(header) {
  const cc = (header || '').toLowerCase();
  const num = (name) => {
    const m = cc.match(new RegExp(`${name}=(\\d+)`));
    return m ? Number(m[1]) : 0;
  };
  return {
    shared: cc.includes('public') && !cc.includes('no-store') && !cc.includes('private'),
    fresh: num('s-maxage'),
    swr: num('stale-while-revalidate'),
    sie: num('stale-if-error'),
  };
}

function upstreamRequest(request, path, origin) {
  const headers = new Headers();
  for (const name of ['accept', 'accept-language', 'authorization', 'content-type', 'origin']) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  // The client's real address, as Cloudflare verified it — not whatever the
  // client claimed in its own X-Forwarded-For. The API rate-limits on this.
  const ip = request.headers.get('cf-connecting-ip');
  if (ip) headers.set('x-forwarded-for', ip);
  headers.set('x-tayari-edge', '1');
  return new Request(origin + path, {
    method: request.method,
    headers,
    body: request.method === 'GET' || request.method === 'HEAD' ? undefined : request.body,
    redirect: 'manual',
  });
}

/** Copy a response with extra headers set. */
function withHeaders(response, extra) {
  const headers = new Headers(response.headers);
  for (const [k, v] of Object.entries(extra)) {
    if (v === null) headers.delete(k);
    else headers.set(k, v);
  }
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

/** Store a 200 response so it survives its whole stale-if-error window. */
async function store(cache, key, response, policy) {
  const keep = policy.fresh + Math.max(policy.swr, policy.sie);
  const stored = withHeaders(response, {
    'cache-control': `public, max-age=${keep}`,
    'x-edge-client-cache-control': response.headers.get('cache-control'),
    'x-edge-stored-at': String(Date.now()),
    'x-edge-fresh': String(policy.fresh),
    'x-edge-swr': String(policy.swr),
    'x-edge-sie': String(policy.sie),
    'set-cookie': null,
    // Render varies on Origin; the key above is already normalised, and a
    // Vary the cache would honour could split one answer into many entries.
    vary: null,
  });
  await cache.put(key, stored);
}

/** Turn a stored entry back into a client response. */
function fromStore(stored, state, ageSeconds) {
  return withHeaders(stored, {
    'cache-control': stored.headers.get('x-edge-client-cache-control') || 'no-cache',
    'x-edge-client-cache-control': null,
    'x-edge-stored-at': null,
    'x-edge-fresh': null,
    'x-edge-swr': null,
    'x-edge-sie': null,
    age: String(ageSeconds),
    'x-tayari-edge': state,
  });
}

async function fetchOrigin(ctx, request, path, timeoutMs) {
  return fetch(upstreamRequest(request, path, ctx.origin), { signal: AbortSignal.timeout(timeoutMs) });
}

/**
 * Fetch from Render and, if Render marked the answer shareable, store it. The
 * store runs in the background so the reader is not kept waiting on it.
 */
async function refresh(ctx, request, path, cache, key, timeoutMs) {
  const response = await fetchOrigin(ctx, request, path, timeoutMs);
  const policy = policyOf(response.headers.get('cache-control'));
  if (response.status === 200 && policy.shared && policy.fresh > 0) {
    ctx.waitUntil(store(cache, key, response.clone(), policy).catch(() => {}));
  }
  return response;
}

function unavailable(message) {
  return new Response(JSON.stringify({ detail: message }), {
    status: 503,
    headers: {
      'content-type': 'application/json',
      'cache-control': 'no-store',
      'retry-after': '30',
      'x-tayari-edge': 'ERROR',
    },
  });
}

/**
 * Serve one API request. `context` is the Pages Functions context: its
 * `waitUntil` lets background refreshes outlive the response.
 */
export async function handle(request, context) {
  const ctx = {
    waitUntil: (promise) => context.waitUntil(promise),
    origin: (context.env && context.env.API_ORIGIN) || DEFAULT_ORIGIN,
  };
  const { waitUntil } = ctx;
  const url = new URL(request.url);
  const path = url.pathname + url.search;

  // Writes, signed-in reads and anything but GET go straight to Render.
  if (request.method !== 'GET' || request.headers.has('authorization')) {
    try {
      const response = await fetchOrigin(ctx, request, path, COLD_WAIT_MS);
      if (response.ok && REPORT_WRITE.test(new URL(path, url).pathname)) {
        // A new report or reply: drop the cached list so the person who just
        // posted sees it on the refresh that follows.
        waitUntil(caches.default.delete(new Request(new URL('/api/reports', url))));
      }
      return withHeaders(response, { 'x-tayari-edge': 'BYPASS' });
    } catch {
      return unavailable('The Tayari server is not responding. Please try again in a minute.');
    }
  }

  const cache = caches.default;
  const upstreamPath = normalise(new URL(path, url));
  const key = new Request(new URL(upstreamPath, url));
  const stored = await cache.match(key);

  if (stored) {
    const age = Math.floor((Date.now() - Number(stored.headers.get('x-edge-stored-at'))) / 1000);
    const fresh = Number(stored.headers.get('x-edge-fresh'));
    const swr = Number(stored.headers.get('x-edge-swr'));
    const sie = Number(stored.headers.get('x-edge-sie'));

    if (age <= fresh) return fromStore(stored, 'HIT', age);

    if (age <= fresh + swr) {
      waitUntil(refresh(ctx, request, upstreamPath, cache, key, COLD_WAIT_MS).catch(() => {}));
      return fromStore(stored, 'STALE', age);
    }

    if (age <= fresh + sie) {
      // Too old to serve without asking — but if Render is asleep or slow, the
      // copy we have beats a spinner. Give it STALE_WAIT_MS, then fall back
      // and let the request finish in the background to refill the cache.
      const attempt = refresh(ctx, request, upstreamPath, cache, key, COLD_WAIT_MS);
      const timer = new Promise((resolve) => setTimeout(() => resolve(null), STALE_WAIT_MS));
      try {
        const response = await Promise.race([attempt, timer]);
        if (response && response.status < 500) {
          return withHeaders(response, { 'x-tayari-edge': 'REVALIDATED' });
        }
      } catch {
        /* fall through to the stored copy */
      }
      waitUntil(attempt.catch(() => {}));
      return fromStore(stored, 'STALE-IF-ERROR', age);
    }
  }

  try {
    const response = await refresh(ctx, request, upstreamPath, cache, key, COLD_WAIT_MS);
    return withHeaders(response, { 'x-tayari-edge': 'MISS' });
  } catch {
    return unavailable(
      'The Tayari server is waking up or unreachable, and there is no recent copy of this answer. Please try again in a minute.'
    );
  }
}
