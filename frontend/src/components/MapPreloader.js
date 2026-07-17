'use client';

import { useEffect } from 'react';
import { warmMap } from '@/lib/perf';
import { MAP_STYLE_URL } from '@/lib/constants';

/**
 * Renders nothing. Sits in the root layout and, on capable devices, warms the
 * map bundle during idle time so navigating to the dashboard feels instant.
 * Deliberately a no-op on the low tier (see `warmMap`).
 */
export default function MapPreloader() {
  useEffect(() => {
    warmMap(MAP_STYLE_URL);
  }, []);
  return null;
}
