'use client';

/**
 * Lazily-loaded Supabase client.
 *
 * `@supabase/supabase-js` is ~228 KB and was previously pulled into the initial
 * bundle of every route (via the AuthProvider in the root layout). Most first
 * visitors never authenticate — they read the onboarding splash and continue as
 * a guest — so we defer the SDK entirely and only import it when it's actually
 * needed: to restore an existing session, or when someone opens the auth flow.
 *
 * A single memoised client is shared across the app (dashboard auth + the Alerts
 * operator console), which also avoids the "Multiple GoTrueClient instances"
 * warning the two old clients produced.
 */

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
// Newer Supabase projects call this the "publishable" key; older ones the "anon"
// key. Accept either so the real key is used regardless of which env var is set.
const SUPABASE_KEY =
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ||
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

let clientPromise = null;

/** Import supabase-js on demand and memoise a single client instance. */
export function getSupabase() {
  if (!clientPromise) {
    clientPromise = import('@supabase/supabase-js').then(({ createClient }) =>
      createClient(SUPABASE_URL, SUPABASE_KEY)
    );
  }
  return clientPromise;
}

/**
 * True when a persisted Supabase session token is present in localStorage — a
 * cheap synchronous signal that lets us tell "definitely logged out" from
 * "maybe logged in" WITHOUT importing the SDK. supabase-js persists under a key
 * shaped like `sb-<project-ref>-auth-token`.
 */
export function hasPersistedSession() {
  if (typeof window === 'undefined') return false;
  try {
    for (let i = 0; i < window.localStorage.length; i++) {
      const key = window.localStorage.key(i);
      if (key && key.startsWith('sb-') && key.endsWith('-auth-token')) return true;
    }
  } catch {
    // Private mode / disabled storage — treat as logged out.
  }
  return false;
}
