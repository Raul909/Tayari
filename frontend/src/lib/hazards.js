/**
 * Client for the multi-hazard API, plus the presentation constants that go
 * with it.
 *
 * Labels, colours and icons are mirrored from the backend registry rather than
 * fetched, so the first paint has them without waiting on a request. The
 * backend remains the authority: `fetchHazardTypes` returns the canonical list
 * including data sources, and the sources page reads from there so what a user
 * is told about provenance can never drift from what the server actually queries.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const HAZARD_META = {
  flood: { label: 'River flooding', short: 'Flood', icon: '🌊', color: '#2E6F8E' },
  earthquake: { label: 'Earthquake', short: 'Quake', icon: '🏚️', color: '#8A5A2B' },
  tsunami: { label: 'Tsunami', short: 'Tsunami', icon: '🌀', color: '#1F5F73' },
  volcano: { label: 'Volcanic activity', short: 'Volcano', icon: '🌋', color: '#A2412A' },
  cyclone: { label: 'Cyclone & severe storm', short: 'Storm', icon: '🌪️', color: '#4C5B8C' },
  extreme_heat: { label: 'Extreme heat', short: 'Heat', icon: '🔥', color: '#C2603A' },
  wildfire: { label: 'Wildfire weather', short: 'Wildfire', icon: '🔥', color: '#B4501F' },
  drought: { label: 'Drought', short: 'Drought', icon: '🏜️', color: '#9A7B3F' },
  landslide: { label: 'Landslide', short: 'Landslide', icon: '⛰️', color: '#6B5B45' },
};

export function hazardMeta(hazard) {
  return HAZARD_META[hazard] || { label: hazard, short: hazard, icon: '⚠️', color: '#6b6558' };
}

/** How fast a hazard arrives, in words the reader can act on. */
export const ONSET_LABELS = {
  instant: 'No warning possible',
  minutes: 'Minutes',
  hours: 'Hours',
  days: 'Days',
  seasons: 'Weeks to months',
};

const STORAGE_KEY = 'tayari.location';

/**
 * Remember the last place the user looked at.
 *
 * Worth doing beyond convenience: this app is most useful to someone checking
 * the same place repeatedly, and on a slow connection re-entering a location
 * every visit is enough friction to stop them checking at all.
 */
export function saveLocation(location) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(location));
  } catch {
    // Private mode or a full quota — not worth failing over.
  }
}

export function loadLocation() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (typeof parsed?.latitude !== 'number' || typeof parsed?.longitude !== 'number') {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function clearLocation() {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* nothing to do */
  }
}

async function getJson(path, { signal } = {}) {
  const res = await fetch(`${API_BASE}${path}`, { signal });
  if (!res.ok) {
    const detail = await res
      .json()
      .then((body) => body?.detail)
      .catch(() => null);
    const error = new Error(detail || `Request failed (${res.status})`);
    error.status = res.status;
    throw error;
  }
  return res.json();
}

/** The full multi-hazard profile for a coordinate. */
export function fetchHazardProfile({ latitude, longitude, name }, options = {}) {
  const params = new URLSearchParams({ lat: latitude, lon: longitude });
  if (name) params.set('name', name);
  return getJson(`/api/hazards?${params}`, options);
}

/** An AI advisory for one hazard, in one language, for one kind of reader. */
export function fetchHazardAdvisory(
  hazard,
  { latitude, longitude, name },
  { role = 'general', language = 'en', signal } = {}
) {
  const params = new URLSearchParams({ lat: latitude, lon: longitude, role, language });
  if (name) params.set('name', name);
  return getJson(`/api/hazards/${hazard}/advisory?${params}`, { signal });
}

/** The hazard catalog, including the data source list shown to the user. */
export function fetchHazardTypes(options = {}) {
  return getJson('/api/hazards/types', options);
}

/** Significant earthquakes and volcanic activity worldwide, for the map. */
export function fetchLiveEvents({ minMagnitude = 4.5, days = 7 } = {}, options = {}) {
  const params = new URLSearchParams({ min_magnitude: minMagnitude, days });
  return getJson(`/api/hazards/events/live?${params}`, options);
}

/** Search for a place by name. */
export function searchPlaces(query, { count = 8, signal } = {}) {
  const params = new URLSearchParams({ q: query, count });
  return getJson(`/api/places/search?${params}`, { signal });
}

/**
 * Ask the browser where we are.
 *
 * Wrapped rather than used raw so the failure modes come back as readable
 * sentences. "User denied Geolocation" is a fine console message and a poor
 * thing to show someone trying to find out if their valley is about to flood.
 */
export function detectLocation({ timeout = 12000 } = {}) {
  return new Promise((resolve, reject) => {
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      reject(new Error('This browser cannot share a location. Search for your place instead.'));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) =>
        resolve({
          latitude: Number(position.coords.latitude.toFixed(4)),
          longitude: Number(position.coords.longitude.toFixed(4)),
          accuracy_m: position.coords.accuracy,
        }),
      (error) => {
        const messages = {
          1: 'Location access was blocked. Allow it in your browser settings, or search for your place instead.',
          2: 'Your location could not be determined. Search for your place instead.',
          3: 'Finding your location took too long. Search for your place instead.',
        };
        reject(new Error(messages[error.code] || 'Could not get your location.'));
      },
      { enableHighAccuracy: false, timeout, maximumAge: 5 * 60 * 1000 }
    );
  });
}

/** Format a coordinate pair for display. */
export function formatCoords(latitude, longitude) {
  const ns = latitude >= 0 ? 'N' : 'S';
  const ew = longitude >= 0 ? 'E' : 'W';
  return `${Math.abs(latitude).toFixed(3)}°${ns}, ${Math.abs(longitude).toFixed(3)}°${ew}`;
}

/** A human label for a place, falling back to coordinates. */
export function placeLabel(location) {
  if (!location) return 'Unknown location';
  const parts = [location.name, location.admin1, location.country].filter(Boolean);
  // admin1 duplicating the city name ("Kathmandu, Kathmandu, Nepal") is common
  // in geocoder output and reads as a bug.
  const unique = parts.filter((part, i) => parts.indexOf(part) === i);
  return unique.length ? unique.join(', ') : formatCoords(location.latitude, location.longitude);
}
