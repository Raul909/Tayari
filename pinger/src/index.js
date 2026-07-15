export default {
  // The scheduled handler is invoked by Cloudflare's Cron Triggers
  async scheduled(event, env, ctx) {
    const renderUrl = "https://tayari-api.onrender.com/health";
    console.log(`[Pinger] Waking up Render app at ${renderUrl}`);

    try {
      const response = await fetch(renderUrl, {
        signal: AbortSignal.timeout(25000), // 25s timeout (Render cold starts can take ~20s)
      });
      if (response.ok) {
        const body = await response.json();
        console.log("[Pinger] Successfully pinged Render app. Status:", response.status, "Body:", JSON.stringify(body));
      } else {
        console.error("[Pinger] Render app returned non-OK status:", response.status);
      }
    } catch (error) {
      console.error("[Pinger] Failed to ping Render app:", error.message || error);
    }
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

    const renderUrl = "https://tayari-api.onrender.com/health";
    try {
      const response = await fetch(renderUrl, {
        signal: AbortSignal.timeout(25000),
      });
      const body = await response.text();
      return new Response(
        JSON.stringify({
          pinger: "tayari-pinger",
          render_status: response.status,
          render_response: body,
          pinged_at: new Date().toISOString(),
        }),
        {
          headers: { "Content-Type": "application/json" },
        }
      );
    } catch (error) {
      return new Response(
        JSON.stringify({
          pinger: "tayari-pinger",
          error: error.message || "Failed to reach Render",
          pinged_at: new Date().toISOString(),
        }),
        {
          status: 502,
          headers: { "Content-Type": "application/json" },
        }
      );
    }
  },
};
