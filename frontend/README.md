# Tayari — Web Dashboard

The coordinator-facing dashboard for **Tayari**, the flood early warning system.
Built with Next.js (App Router) and vanilla CSS.

## What's here

- **Dashboard (`/`)** — a MapLibre map of the monitored basins with live risk
  markers, community report pins, a risk gauge, a 7-day discharge chart, an
  impact assessment, and role/language-tailored advisories.
- **Alerts (`/alerts`)** — compose and send multilingual SMS advisories, with a
  live SMS preview and a send history.
- **Report (`/report`)** — submit geotagged community reports that show up as
  pins on the dashboard map.

## Getting started

The dashboard talks to the FastAPI backend (default `http://localhost:8000`).
Start the backend first (see the root `README.md`), then:

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Point the app at a non-default backend with an env var:

```bash
NEXT_PUBLIC_API_URL=https://your-api.example.com npm run dev
```

## Design notes

The UI is intentionally calm and minimal — a warm paper background, one
terracotta accent, muted (but still unambiguous) risk colours, and system fonts
(no web-font fetch, so nothing blocks first paint). The map does the talking.

## Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start the dev server |
| `npm run build` | Production build |
| `npm run start` | Serve the production build |
| `npm run lint` | Lint |
