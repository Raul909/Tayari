# Tayari — Web Dashboard

The web front end for **Tayari**, the multi-hazard early warning and early
action system. Built with Next.js 16 (App Router) and vanilla CSS, statically
exported and served from Cloudflare Pages at
**[tayari.pages.dev](https://tayari.pages.dev)**.

It is a client of the FastAPI backend — there is no server-side rendering at
request time and no API routes here. Every page runs in the browser and talks to
the backend over `NEXT_PUBLIC_API_URL`.

## What's here

The app opens on a **location**, not on a river. You give it a place, and it
answers what threatens you there and what to do about it.

- **My area (`/`)** — the multi-hazard dashboard. Search a place (or share your
  location) and Tayari scores nine hazards for that coordinate: river flooding,
  earthquake, tsunami, volcanic activity, cyclone & severe storm, extreme heat,
  wildfire weather, drought and landslide. Each hazard is a card carrying its own
  risk level and reasoning; selecting one opens a detail panel with the numbers
  behind it and role- and language-tailored advisories. Hazards with no physical
  basis at that location are screened out and listed separately, so a landlocked
  town never sees a tsunami card. A MapLibre map alongside shows the pin for your
  location plus live worldwide earthquakes (M4.5+, last 7 days) and erupting
  volcanoes.
- **Hazards (`/hazards`)** — the hazard guide. What each of the nine hazards is,
  how much warning it gives, whether it can be forecast at all, and where its
  numbers come from (read from the backend registry, so provenance can't drift
  from what the server actually queries). Deep-linkable: `/hazards?h=volcano`
  opens that hazard directly. The flood entry links through to the eight
  calibrated basins.
- **Alerts (`/alerts`)** — send an advisory to a phone. The flow is hazard first,
  then place: pick what you're worried about, pick where, and Tayari works out
  whether that hazard is even relevant there before generating a live SMS preview
  in the chosen role and language. Signing in from the page header attaches your
  token to the send, which is what puts it in the alert history listed underneath.
- **Report (`/report`)** — submit geotagged community flood reports with an
  optional photo, and read the report feed with its advice threads. Reports are
  filed against one of the eight basins and appear as pins on the basin map.
- **Basins (`/basins`)** — the original eight-basin flood dashboard: risk
  markers, a risk gauge, a 7-day discharge chart, an impact assessment and
  advisories. Still the more trustworthy answer where it applies, because those
  eight rivers are calibrated against documented historical floods rather than
  estimated from a five-year record. It is no longer a top-level destination —
  it is reached from the flood hazard, which is what it is a detail of.
- **Reset password (`/reset-password`)** — the landing page for the Supabase
  password-reset email.

### Navigation and accounts

Navigation is a top bar on desktop and a fixed bottom tab bar on phones (four
destinations don't fit across a 360 px viewport without clipping). Auth is
Supabase: you can sign in, or continue as a guest from the onboarding splash and
use the app without an account. Signing in is what ties sent alerts to you.

### Built for slow phones and metered data

The map is a ~1.2 MB WebGL bundle plus cross-origin tiles, which is fine on a
laptop and punishing on a 2 GB Android over 2G — exactly the user this app exists
for. So `lib/perf.js` grades each visitor into a tier from device memory, CPU
core count and the Network Information API:

| Tier | Behaviour |
|---|---|
| `high` | Full experience; the map bundle is warmed during idle time |
| `mid` | Map loads after first paint, no idle warm |
| `low` (low-RAM / 2G / Save-Data) | Map is **not** downloaded — the user opts in with a tap |

Chart.js is dynamically imported so it never reaches a first paint that doesn't
need it, cross-origin origins (tiles, API, Supabase) are preconnected from the
document head, and the UI uses system fonts so nothing blocks first paint.

## Getting started

Start the FastAPI backend first (see the root `README.md`); the dashboard
defaults to `http://localhost:8000`.

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Environment

`.env.development` already points the dev server at a local backend. For
anything else, set these `NEXT_PUBLIC_*` vars — they're inlined at build time, so
a change means a rebuild:

| Variable | Required | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | No — defaults to `http://localhost:8000` | The FastAPI backend |
| `NEXT_PUBLIC_SUPABASE_URL` | For accounts | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | For accounts | Supabase publishable key (`NEXT_PUBLIC_SUPABASE_ANON_KEY` is also accepted) |

Without the Supabase vars the app still runs — it falls back to guest mode.

Point a dev server at a non-default backend inline:

```bash
NEXT_PUBLIC_API_URL=https://your-api.example.com npm run dev
```

## Backend endpoints this app calls

Multi-hazard: `/api/hazards`, `/api/hazards/types`,
`/api/hazards/{hazard}/advisory`, `/api/hazards/events/live`,
`/api/alerts/hazard/send`, `/api/places/search`.

Basins and community: `/api/basins`, `/api/forecasts/{id}` (+ `/history`),
`/api/advisory/{id}`, `/api/alerts/send`, `/api/alerts/history`, `/api/reports`
(+ `/upload`, `/{id}/advice`), `/api/chat/{id}`, `/api/feedback`.

## Design notes

The UI is intentionally calm and minimal — a warm paper background, one
terracotta accent, muted (but still unambiguous) risk colours, and system fonts.
The map does the talking.

Two things the risk display deliberately keeps apart: **susceptibility** ("can
this happen here at all?") and **score** ("is it happening now?"). A coastal
city's tsunami susceptibility is permanently high, and rendering that as a
permanently high *risk* is the alarm fatigue that gets the one real warning
ignored — so an exposed-but-quiet place reads as exactly that.

Pinch-zoom is never locked, and the layout pads with `env(safe-area-inset-*)` for
notched phones.

## Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start the dev server |
| `npm run build` | Static export to `out/` |
| `npm run build:prod` | Static export pointed at the production API |
| `npm run deploy` | Production build, then `wrangler pages deploy out` |
| `npm run start` | Serve the production build |
| `npm run lint` | Lint |

## Deployment

`next.config.mjs` sets `output: 'export'`, so a build produces a fully static
`out/` directory. `wrangler.toml` publishes it to Cloudflare Pages as the
`tayari` project. `npm run deploy` does both in one step.

---

**Working on this app?** Read `AGENTS.md` first — this is Next.js 16, and its
APIs and conventions differ from older versions.
