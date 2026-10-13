/**
 * Words and labels for hazards and risk levels, with no dependencies.
 *
 * Shared by the web app and the edge functions that serve the lite pages
 * (edge/lite.js), which run outside the browser and outside Next.js. Keeping
 * these in one plain module means a hazard is called the same thing on the
 * full site, on a basic phone and in every advisory link.
 */

export const HAZARD_META = {
  flood: { label: 'River flooding', short: 'Flood', icon: 'flood', color: '#2E6F8E' },
  earthquake: { label: 'Earthquake', short: 'Quake', icon: 'earthquake', color: '#8A5A2B' },
  tsunami: { label: 'Tsunami', short: 'Tsunami', icon: 'tsunami', color: '#1F5F73' },
  volcano: { label: 'Volcanic activity', short: 'Volcano', icon: 'volcano', color: '#A2412A' },
  cyclone: { label: 'Cyclone & severe storm', short: 'Storm', icon: 'cyclone', color: '#4C5B8C' },
  extreme_heat: { label: 'Extreme heat', short: 'Heat', icon: 'thermostat', color: '#C2603A' },
  wildfire: { label: 'Wildfire weather', short: 'Wildfire', icon: 'local_fire_department', color: '#B4501F' },
  drought: { label: 'Drought', short: 'Drought', icon: 'wb_sunny', color: '#9A7B3F' },
  landslide: { label: 'Landslide', short: 'Landslide', icon: 'landslide', color: '#6B5B45' },
};

export function hazardMeta(hazard) {
  return HAZARD_META[hazard] || { label: hazard, short: hazard, icon: 'warning', color: '#6b6558' };
}

/** How fast a hazard arrives, in words the reader can act on. */
export const ONSET_LABELS = {
  instant: 'No warning possible',
  minutes: 'Minutes',
  hours: 'Hours',
  days: 'Days',
  seasons: 'Weeks to months',
};

/** The overall level as an answer rather than a label. */
export const RISK_WORDS = {
  LOW: 'All clear for now',
  MODERATE: 'Stay alert',
  HIGH: 'Take action',
  EXTREME: 'Act now — danger',
};

// One-tap starting points for someone who just wants to see what this does,
// spread across the hazards and the regions Tayari was built for.
export const EXAMPLE_PLACES = [
  { name: 'Beledweyne', country: 'Somalia', country_code: 'so', latitude: 4.74, longitude: 45.2 },
  { name: 'Nairobi', country: 'Kenya', country_code: 'ke', latitude: -1.2864, longitude: 36.8172 },
  { name: 'Jakarta', country: 'Indonesia', country_code: 'id', latitude: -6.2088, longitude: 106.8456 },
  { name: 'Manila', country: 'Philippines', country_code: 'ph', latitude: 14.5995, longitude: 120.9842 },
  { name: 'Naples', country: 'Italy', country_code: 'it', latitude: 40.8518, longitude: 14.2681 },
];
