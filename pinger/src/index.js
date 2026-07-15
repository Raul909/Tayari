export default {
  // The scheduled handler is invoked by Cloudflare's Cron Triggers
  async scheduled(event, env, ctx) {
    const renderUrl = "https://tayari-api.onrender.com/health";
    console.log(`[Pinger] Waking up Render app at ${renderUrl}`);

    try {
      const response = await fetch(renderUrl);
      if (response.ok) {
        console.log("[Pinger] Successfully pinged Render app. Status:", response.status);
      } else {
        console.error("[Pinger] Render app returned non-OK status:", response.status);
      }
    } catch (error) {
      console.error("[Pinger] Failed to ping Render app:", error);
    }
  },
};
