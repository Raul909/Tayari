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
