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

    // Proxy for Open-Meteo Flood API
    if (url.pathname.startsWith("/flood")) {
      const target = new URL("https://flood-api.open-meteo.com/v1/flood" + url.search);
      const resp = await fetch(target, { headers: { "User-Agent": "Tayari CF Worker" } });
      return new Response(resp.body, { status: resp.status, headers: { "Content-Type": "application/json" } });
    }

    // Proxy for Open-Meteo Weather API
    if (url.pathname.startsWith("/weather")) {
      const target = new URL("https://api.open-meteo.com/v1/forecast" + url.search);
      const resp = await fetch(target, { headers: { "User-Agent": "Tayari CF Worker" } });
      return new Response(resp.body, { status: resp.status, headers: { "Content-Type": "application/json" } });
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
