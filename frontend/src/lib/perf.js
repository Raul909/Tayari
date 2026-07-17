'use client';

/**
 * Device performance tiering.
 *
 * The interactive map is a ~1.2 MB WebGL bundle plus cross-origin tiles. That is
 * a fine cost on a laptop and a punishing one for a farmer on a 2 GB Android over
 * a 2G/Save-Data connection — exactly the user this app exists for. So we grade
 * each visitor into a tier and adapt how (and whether) we auto-load the map:
 *
 *   high — desktop / recent phones on good networks. Full experience, and we
 *          warm the map bundle during idle time so it renders instantly.
 *   mid  — average phones / 3G. Load the map after first paint, no idle warm.
 *   low  — low-RAM / 2G / Save-Data. Don't auto-download the map at all; let the
 *          user opt in with a tap so we never spend a metered byte uninvited.
 */

export const TIERS = { HIGH: 'high', MID: 'mid', LOW: 'low' };

/** The Network Information API, prefixed across engines. `{}` when unavailable. */
export function getConnection() {
  if (typeof navigator === 'undefined') return {};
  return (
    navigator.connection ||
    navigator.mozConnection ||
    navigator.webkitConnection ||
    {}
  );
}

export function prefersSaveData() {
  return !!getConnection().saveData;
}

/**
 * Grade the current device/connection. Runs on the client only; during the
 * static build (no `navigator`) we assume `high` so prerendered markup never
 * gates a feature that the real device could handle.
 */
export function getDeviceTier() {
  if (typeof navigator === 'undefined') return TIERS.HIGH;

  const mem = navigator.deviceMemory; // GB — Chromium only, undefined elsewhere
  const cores = navigator.hardwareConcurrency; // logical cores, widely supported
  const conn = getConnection();
  const et = conn.effectiveType || '';
  const saveData = !!conn.saveData;

  // Hard "low" signals: the user asked to save data, or the link is genuinely slow.
  if (saveData || et === 'slow-2g' || et === '2g') return TIERS.LOW;
  if ((mem && mem <= 2) || (cores && cores <= 2)) return TIERS.LOW;

  // "mid" signals: 3G, or modest RAM / core counts.
  if (et === '3g' || (mem && mem <= 4) || (cores && cores <= 4)) return TIERS.MID;

  return TIERS.HIGH;
}

/**
 * MapLibre constructor overrides tuned per tier. Merged over the base config, so
 * `high` intentionally returns `{}` (library defaults).
 */
export function mapOptionsForTier(tier) {
  if (tier === TIERS.LOW) {
    return {
      fadeDuration: 0, // no cross-fade → far less compositing on weak GPUs
      maxTileCacheSize: 20, // cap memory on low-RAM devices
      refreshExpiredTiles: false, // stop background re-fetches over metered links
    };
  }
  if (tier === TIERS.MID) {
    return {
      fadeDuration: 120,
      maxTileCacheSize: 40,
    };
  }
  return {};
}

/**
 * `requestIdleCallback` with a `setTimeout` fallback (Safari lacks rIC). Returns
 * a canceller so callers can bail on unmount.
 */
export function onIdle(cb, timeout = 2000) {
  if (typeof window === 'undefined') return () => {};
  if ('requestIdleCallback' in window) {
    const id = window.requestIdleCallback(cb, { timeout });
    return () => window.cancelIdleCallback(id);
  }
  const id = window.setTimeout(cb, 200);
  return () => window.clearTimeout(id);
}

let mapModulePromise = null;
/**
 * Import maplibre-gl once and share the promise. Both the idle warm-up and the
 * dashboard's own init call this, so the 1.2 MB module is fetched a single time
 * no matter which fires first.
 */
export function loadMapLibrary() {
  if (!mapModulePromise) {
    mapModulePromise = import('maplibre-gl').then((m) => m.default || m);
  }
  return mapModulePromise;
}

let warmed = false;
/**
 * Warm the map bundle (and prime the HTTP cache for the style descriptor) during
 * idle time, so the first real map render is instant — useful while the visitor
 * reads the onboarding splash or sits on the Alerts/Report pages. Skipped on the
 * low tier so we never download a megabyte the user didn't ask for.
 */
export function warmMap(styleUrl) {
  if (warmed || typeof window === 'undefined') return;
  if (getDeviceTier() === TIERS.LOW) return;
  warmed = true;
  onIdle(() => {
    loadMapLibrary().catch(() => {});
    if (styleUrl) {
      fetch(styleUrl, { mode: 'cors' }).catch(() => {});
    }
  }, 3000);
}
