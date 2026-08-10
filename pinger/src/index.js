export default {
  // The scheduled handler is invoked by Cloudflare's Cron Triggers.
  async scheduled(event, env, ctx) {
    const base = "https://tayari-api.onrender.com";
    // /health keeps the Render free tier warm (spins down after 15 min idle).
    // /health/db runs a SELECT 1 so the managed Postgres (Supabase) never pauses
    // from inactivity. Fire both and tolerate either failing — a DB blip must
    // not stop us waking Render, and vice versa.
    const paths = ["/health", "/health/db"];
    const results = await Promise.allSettled(
      paths.map((path) =>
        fetch(base + path, { signal: AbortSignal.timeout(25000) })
      )
    );
    results.forEach((r, i) => {
      if (r.status === "fulfilled") {
        console.log(`[Pinger] ${paths[i]} -> HTTP ${r.value.status}`);
      } else {
        console.error(`[Pinger] ${paths[i]} failed:`, r.reason?.message || r.reason);
      }
    });
  },

  // Optional: allow manual pings via HTTP for debugging
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Upstream feeds proxied on the backend's behalf.
    //
    // Open-Meteo rate-limits Render's egress IP, while the same requests
    // succeed from Cloudflare's edge. USGS and the Smithsonian GeoServer are
    // reachable from Render directly and are not proxied.
    const PROXY_ROUTES = {
      "/flood": "https://flood-api.open-meteo.com/v1/flood",
      "/weather": "https://api.open-meteo.com/v1/forecast",
      "/archive": "https://archive-api.open-meteo.com/v1/archive",
      "/elevation": "https://api.open-meteo.com/v1/elevation",
      "/geocode": "https://geocoding-api.open-meteo.com/v1/search",
      "/revgeo": "https://api.bigdatacloud.net/data/reverse-geocode-client",
    };

    for (const [prefix, upstream] of Object.entries(PROXY_ROUTES)) {
      if (url.pathname.startsWith(prefix)) {
        try {
          const resp = await fetch(upstream + url.search, {
            headers: { "User-Agent": "Tayari CF Worker" },
            // The reanalysis archive can take a while for a five-year window.
            signal: AbortSignal.timeout(50000),
          });
          const responseHeaders = new Headers();
          responseHeaders.set(
            "Content-Type",
            resp.headers.get("Content-Type") || "application/json"
          );
          // Cached at the edge so repeated lookups for the same place cost the
          // upstream nothing. Short, because the forecast half moves hourly.
          responseHeaders.set("Cache-Control", "public, max-age=600");
          return new Response(resp.body, { status: resp.status, headers: responseHeaders });
        } catch (error) {
          return new Response(
            JSON.stringify({ error: `Upstream fetch failed: ${error.message || error}` }),
            { status: 502, headers: { "Content-Type": "application/json" } }
          );
        }
      }
    }

    // Manual ping — reports both the Render wake and the Supabase DB touch, so
    // you can verify the keep-alive on demand (visit the Worker URL directly).
    const base = "https://tayari-api.onrender.com";
    async function hit(path) {
      try {
        const resp = await fetch(base + path, { signal: AbortSignal.timeout(25000) });
        return { status: resp.status, body: await resp.text() };
      } catch (error) {
        return { status: 0, error: error.message || String(error) };
      }
    }
    const [render, db] = await Promise.all([hit("/health"), hit("/health/db")]);
    return new Response(
      JSON.stringify({
        pinger: "tayari-pinger",
        render,
        database: db,
        pinged_at: new Date().toISOString(),
      }),
      {
        status: render.status === 200 ? 200 : 502,
        headers: { "Content-Type": "application/json" },
      }
    );
  },
};
