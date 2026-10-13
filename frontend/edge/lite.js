/**
 * Tayari Lite: the whole warning service as plain HTML, for any phone.
 *
 * The main site is a JavaScript application with a WebGL map. That is right for
 * most people and useless for some of the people Tayari exists for: a Nokia on
 * Symbian, a KaiOS feature phone, Opera Mini squeezing pages through a proxy, a
 * ten-year-old Android stuck on its first browser, anyone paying for every
 * kilobyte. A warning that only reaches modern phones is missing the people
 * least able to recover from a disaster.
 *
 * So these pages are rendered at the edge as HTML 4-era markup: links, GET
 * forms, one small style block, no script anywhere. Each is a few kilobytes and
 * works with JavaScript off, images off and CSS ignored. The data comes through
 * the same edge gateway as the main site, with the same cache, so the lite pages
 * stay up when the API is asleep exactly as the full site does.
 *
 * Old browsers are sent here automatically (see the gate script in
 * src/app/layout.js), and every lite page links to the full version.
 */

import { handle } from './gateway.js';
import { EXAMPLE_PLACES, HAZARD_META, ONSET_LABELS, RISK_WORDS } from '../src/lib/hazard-meta.js';
import { LANGUAGE_LABELS, ROLES } from '../src/lib/constants.js';

// FormSubmit's alias for the feedback inbox — see backend/app/routers/feedback.py.
const FORMSUBMIT_FORM = 'https://formsubmit.co/bc7b96d4113e366589fd2e528232a340';

const STYLE = `
body{margin:0;padding:10px;font-family:sans-serif;background:#faf9f6;color:#23211c;line-height:1.45;max-width:40em}
a{color:#9c4826}
h1{font-size:1.3em;margin:.4em 0}
h2{font-size:1.1em;margin:1em 0 .3em}
.top{border-bottom:1px solid #d8d3c7;padding-bottom:6px;margin-bottom:8px}
.top b{font-size:1.15em}
.box{border:1px solid #d8d3c7;background:#fff;padding:8px;margin:8px 0}
.muted,small{color:#6b6558}
.low{color:#3f7d53}.moderate{color:#7f5c1d}.high{color:#c0432b}.extreme{color:#83291a}
.lvl{font-weight:bold}
.warn{border-left:4px solid #b0812c;padding-left:8px}
li{margin-bottom:6px}
.foot{border-top:1px solid #d8d3c7;margin-top:16px;padding-top:6px;font-size:.9em}
`;

function esc(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function query(params) {
  return Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&');
}

function page(title, body, { status = 200, cache = 'no-cache' } = {}) {
  const html =
    `<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">` +
    `<meta name="viewport" content="width=device-width, initial-scale=1">` +
    `<meta name="HandheldFriendly" content="true"><meta name="MobileOptimized" content="width">` +
    `<title>${esc(title)} — Tayari</title><style>${STYLE}</style></head><body>` +
    `<div class="top"><a href="/lite"><b>Tayari</b></a> <span class="muted">Hazard warnings</span></div>` +
    body +
    `<div class="foot"><a href="/lite">Home</a> · <a href="/lite/feedback">Feedback</a> · ` +
    `<a href="/?full=1">Full version</a><br><small>Simple version: works on any phone, no JavaScript needed.</small></div>` +
    `</body></html>`;
  return new Response(html, {
    status,
    headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': cache },
  });
}

function searchForm(value = '') {
  return (
    `<form action="/lite/find" method="get"><label for="q">Town or city</label><br>` +
    `<input id="q" name="q" type="text" size="22" value="${esc(value)}"> ` +
    `<input type="submit" value="Check"></form>`
  );
}

function levelSpan(level) {
  return `<span class="lvl ${esc(String(level).toLowerCase())}">${esc(level)}</span>`;
}

function placeName(p) {
  return [p.name, p.country].filter(Boolean).join(', ') || `${Number(p.latitude).toFixed(3)}, ${Number(p.longitude).toFixed(3)}`;
}

function when(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getUTCDate()} ${months[d.getUTCMonth()]} ${d.getUTCFullYear()}, ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
}

/** Call the API through the edge gateway, without leaving this worker. */
async function api(request, context, path) {
  const apiRequest = new Request(new URL(path, request.url), { headers: request.headers });
  const response = await handle(apiRequest, context);
  const state = response.headers.get('x-tayari-edge') || '';
  const age = Number(response.headers.get('age') || 0);
  let data = null;
  try {
    data = await response.json();
  } catch {
    /* not JSON — treated as a failure below */
  }
  return { ok: response.ok, status: response.status, data, stale: state === 'STALE-IF-ERROR', age };
}

function staleNote(result) {
  if (!result.stale) return '';
  const minutes = Math.max(1, Math.round(result.age / 60));
  return `<p class="box warn">The live service is not responding, so this is the last answer Tayari saved, from about ${minutes} minute${minutes === 1 ? '' : 's'} ago.</p>`;
}

function failure(title, result, retryHref) {
  const busy = result.status === 503 || result.status === 502 || result.status === 504 || result.status === 0;
  const message = busy
    ? 'The Tayari server is waking up or busy. This can take up to a minute on the first visit.'
    : (result.data && result.data.detail) || 'Something went wrong.';
  return page(
    title,
    `<h1>${esc(title)}</h1><p>${esc(message)}</p><p><a href="${esc(retryHref)}">Try again</a></p>`,
    { status: busy ? 503 : 200 }
  );
}

function coords(url) {
  const lat = Number(url.searchParams.get('lat'));
  const lon = Number(url.searchParams.get('lon'));
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) return null;
  return {
    latitude: lat,
    longitude: lon,
    name: url.searchParams.get('name') || '',
    country: url.searchParams.get('country') || '',
    country_code: (url.searchParams.get('country_code') || '').toLowerCase(),
  };
}

function areaHref(p) {
  return `/lite/area?${query({ lat: p.latitude, lon: p.longitude, name: p.name, country: p.country, country_code: p.country_code })}`;
}

// ─── Pages ──────────────────────────────────────────────────────────────────

function home(request) {
  const cf = request.cf || {};
  const near = cf.city && cf.latitude && cf.longitude
    ? `<p><a href="/lite/near">Use my approximate location (${esc(cf.city)})</a><br><small>Worked out from your network, so it may be the nearest city rather than your town.</small></p>`
    : '';
  const examples = EXAMPLE_PLACES.map((p) => `<li><a href="${esc(areaHref(p))}">${esc(placeName(p))}</a></li>`).join('');
  return page(
    'What threatens where you are?',
    `<h1>What threatens where you are?</h1>` +
      `<p>Tayari checks nine hazards (floods, earthquakes, tsunami, volcanoes, storms, heat, wildfire, drought and landslides) against live data, then tells you what to do. Free, no account needed.</p>` +
      searchForm() +
      near +
      `<h2>Or try</h2><ul>${examples}</ul>`,
    { cache: 'public, max-age=300' }
  );
}

async function find(request, context, url) {
  const q = (url.searchParams.get('q') || '').trim();
  if (q.length < 2) {
    return page('Find a place', `<h1>Find a place</h1><p>Type at least two letters.</p>${searchForm(q)}`);
  }
  const result = await api(request, context, `/api/places/search?${query({ q, count: 8 })}`);
  if (!result.ok) return failure('Find a place', result, `/lite/find?${query({ q })}`);
  const places = Array.isArray(result.data) ? result.data : [];
  if (places.length === 0) {
    return page(
      'No places found',
      `<h1>No places found</h1><p>Nothing matched “${esc(q)}”. Check the spelling, or try a larger town nearby.</p>${searchForm(q)}`
    );
  }
  const items = places
    .map((p) => {
      const detail = [p.admin1, p.country].filter(Boolean).join(', ');
      return `<li><a href="${esc(areaHref(p))}">${esc(p.name)}</a>${detail ? ` <small>${esc(detail)}</small>` : ''}</li>`;
    })
    .join('');
  return page('Choose your place', `<h1>Choose your place</h1><ul>${items}</ul>${searchForm(q)}`);
}

function near(request) {
  const cf = request.cf || {};
  if (!cf.latitude || !cf.longitude) {
    return Response.redirect(new URL('/lite', request.url).toString(), 302);
  }
  const target = areaHref({
    latitude: Number(cf.latitude).toFixed(4),
    longitude: Number(cf.longitude).toFixed(4),
    name: cf.city || '',
    country: cf.country || '',
    country_code: (cf.country || '').toLowerCase(),
  });
  return Response.redirect(new URL(target, request.url).toString(), 302);
}

async function area(request, context, url) {
  const place = coords(url);
  if (!place) return Response.redirect(new URL('/lite', request.url).toString(), 302);

  const result = await api(
    request,
    context,
    `/api/hazards?${query({ lat: place.latitude, lon: place.longitude, name: place.name, country: place.country, country_code: place.country_code })}`
  );
  if (!result.ok || !result.data) return failure(placeName(place), result, areaHref(place));

  const profile = result.data;
  const level = profile.overall_risk;
  const hazards = (profile.hazards || [])
    .map((risk) => {
      const meta = HAZARD_META[risk.hazard] || { label: risk.label };
      const href = `/lite/hazard?${query({ h: risk.hazard, lat: place.latitude, lon: place.longitude, name: place.name, country: place.country, country_code: place.country_code })}`;
      const notes = [ONSET_LABELS[risk.onset] || risk.onset];
      if (risk.risk_level === 'LOW' && risk.susceptibility >= 0.5) notes.push('Exposed area, quiet right now');
      if (risk.degraded) notes.push('Partial data');
      return `<li><a href="${esc(href)}"><b>${esc(meta.label)}</b></a> ${levelSpan(risk.risk_level)}<br>${esc(risk.headline)}<br><small>${esc(notes.join(' · '))}</small></li>`;
    })
    .join('');
  const screened = (profile.screened_out || []).map((h) => (HAZARD_META[h] || { short: h }).short).join(', ');

  return page(
    placeName(place),
    `<p class="muted">Showing</p><h1>${esc(placeName(place))}</h1>` +
      staleNote(result) +
      `<div class="box"><span class="lvl ${esc(String(level).toLowerCase())}">${esc(RISK_WORDS[level] || level)}</span><br>${esc(profile.headline)}</div>` +
      (profile.partial ? `<p class="muted">Some data feeds did not respond, so a hazard may be missing.</p>` : '') +
      `<h2>${(profile.hazards || []).length} hazards checked</h2><p class="muted">Choose one for what to do.</p><ol>${hazards}</ol>` +
      (screened ? `<p class="muted">Not relevant here: ${esc(screened)}. Tayari checked and found no physical basis for these at this location.</p>` : '') +
      `<p><small>Checked ${esc(when(profile.generated_at))}.</small></p>` +
      `<h2>Check somewhere else</h2>${searchForm()}`
  );
}

async function hazard(request, context, url) {
  const place = coords(url);
  const h = url.searchParams.get('h') || '';
  if (!place || !/^[a-z_]+$/.test(h)) return Response.redirect(new URL('/lite', request.url).toString(), 302);
  const role = url.searchParams.get('role') || 'general';
  const lang = url.searchParams.get('lang') || 'en';
  const meta = HAZARD_META[h] || { label: h };
  const back = areaHref(place);
  const self = `/lite/hazard?${query({ h, lat: place.latitude, lon: place.longitude, name: place.name, country: place.country, country_code: place.country_code, role, lang })}`;

  const result = await api(
    request,
    context,
    `/api/hazards/${h}/advisory?${query({ lat: place.latitude, lon: place.longitude, name: place.name, country: place.country, country_code: place.country_code, role, language: lang })}`
  );
  if (!result.ok || !result.data) return failure(meta.label, result, self);

  const { advisory, risk } = result.data;
  const dir = advisory.language === 'ar' ? ' dir="rtl"' : '';
  const actions = (advisory.actions || []).map((a) => `<li>${esc(a)}</li>`).join('');
  const fallback =
    advisory.requested_language && advisory.language !== advisory.requested_language
      ? `<p class="muted">Shown in ${esc(LANGUAGE_LABELS[advisory.language] || advisory.language)}: ${esc(LANGUAGE_LABELS[advisory.requested_language] || advisory.requested_language)} is not available right now.</p>`
      : '';
  const indicators = (risk.indicators || [])
    .map((i) => `<li>${esc(i.label)}: <b>${esc(i.value)}</b>${i.trend ? ` (${esc(i.trend)})` : ''}${i.detail ? `<br><small>${esc(i.detail)}</small>` : ''}</li>`)
    .join('');
  const sources = (risk.data_sources || []).map((s) => `<li>${esc(s)}</li>`).join('');
  const option = (value, label, current) => `<option value="${esc(value)}"${value === current ? ' selected' : ''}>${esc(label)}</option>`;

  return page(
    `${meta.label} at ${placeName(place)}`,
    `<p><a href="${esc(back)}">Back to all hazards</a></p>` +
      `<h1>${esc(meta.label)}</h1><p>${levelSpan(risk.risk_level)} · ${esc(ONSET_LABELS[risk.onset] || risk.onset)} · ${esc(placeName(place))}</p>` +
      staleNote(result) +
      `<p><b>${esc(risk.headline)}</b></p>` +
      (risk.summary ? `<p>${esc(risk.summary)}</p>` : '') +
      `<h2>What to do</h2>` +
      `<div class="box"${dir}><b>${esc(advisory.title)}</b><p>${esc(advisory.body)}</p>${actions ? `<ol>${actions}</ol>` : ''}</div>` +
      fallback +
      `<p><small>${
        advisory.ai_generated
          ? 'Written by AI, which can make mistakes. Check critical details with official sources before acting.'
          : 'Standard safety guidance, written and reviewed by people.'
      }</small></p>` +
      `<form action="/lite/hazard" method="get">` +
      ['h', 'lat', 'lon', 'name', 'country', 'country_code']
        .map((k) => `<input type="hidden" name="${k}" value="${esc(k === 'h' ? h : k === 'lat' ? place.latitude : k === 'lon' ? place.longitude : place[k])}">`)
        .join('') +
      `<label for="role">Written for</label><br><select id="role" name="role">${ROLES.map((r) => option(r.value, r.label, role)).join('')}</select><br>` +
      `<label for="lang">Language</label><br><select id="lang" name="lang">${Object.entries(LANGUAGE_LABELS).map(([v, l]) => option(v, l, lang)).join('')}</select><br>` +
      `<input type="submit" value="Show advice"></form>` +
      (indicators ? `<h2>What this is based on</h2><ul>${indicators}</ul>` : '') +
      (sources ? `<h2>Where this comes from</h2><ul>${sources}</ul>` : '')
  );
}

function feedback(request) {
  const next = new URL('/lite/thanks', request.url).toString();
  const ratings = [5, 4, 3, 2, 1]
    .map((n) => {
      const label = ['', 'Very poor', 'Poor', 'Okay', 'Good', 'Very good'][n];
      return `<option value="${n}/5 – ${label}">${n} – ${label}</option>`;
    })
    .join('');
  return page(
    'Feedback',
    `<h1>Your feedback</h1>` +
      `<form action="${FORMSUBMIT_FORM}" method="post">` +
      `<input type="hidden" name="_subject" value="Tayari Feedback (simple version)">` +
      `<input type="hidden" name="_next" value="${esc(next)}">` +
      `<input type="hidden" name="_captcha" value="false">` +
      `<input type="hidden" name="_template" value="table">` +
      `<input type="hidden" name="version" value="Simple version (/lite)">` +
      // A field people never see and bots fill in; FormSubmit drops those.
      `<input type="text" name="_honey" value="" style="display:none" tabindex="-1" autocomplete="off">` +
      `<label for="rating">How would you rate Tayari?</label><br><select id="rating" name="rating">${ratings}</select><br>` +
      `<label for="subject">Subject</label><br><select id="subject" name="subject"><option>Suggestion</option><option>Bug</option><option>Other</option></select><br>` +
      `<label for="message">Comment (optional)</label><br><textarea id="message" name="message" rows="4" cols="28"></textarea><br>` +
      `<input type="submit" value="Send feedback"></form>`,
    { cache: 'public, max-age=3600' }
  );
}

function thanks() {
  return page('Thank you', `<h1>Thank you</h1><p>Your feedback was sent.</p><p><a href="/lite">Back to Tayari</a></p>`);
}

/** Route a /lite request. */
export async function lite(request, context) {
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    return new Response('Method not allowed', { status: 405 });
  }
  const url = new URL(request.url);
  const path = url.pathname.replace(/\/+$/, '') || '/lite';
  try {
    switch (path) {
      case '/lite':
        return home(request);
      case '/lite/find':
        return await find(request, context, url);
      case '/lite/near':
        return near(request);
      case '/lite/area':
        return await area(request, context, url);
      case '/lite/hazard':
        return await hazard(request, context, url);
      case '/lite/feedback':
        return feedback(request);
      case '/lite/thanks':
        return thanks();
      default:
        return page('Not found', `<h1>Page not found</h1><p><a href="/lite">Go to Tayari</a></p>`, { status: 404 });
    }
  } catch {
    return failure('Tayari', { status: 503, data: null }, url.pathname + url.search);
  }
}
