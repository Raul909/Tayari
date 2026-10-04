'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import 'maplibre-gl/dist/maplibre-gl.css';
import HazardCard from '@/components/HazardCard';
import HazardDetail from '@/components/HazardDetail';
import LocationBar from '@/components/LocationBar';
import { useToast } from '@/components/Toast';
import { MAP_STYLE_URL, RISK_COLORS } from '@/lib/constants';
import {
  fetchHazardProfile,
  fetchLiveEvents,
  hazardMeta,
  loadLocation,
  placeLabel,
  reverseGeocode,
  saveLocation,
} from '@/lib/hazards';
import { getDeviceTier, loadMapLibrary, mapOptionsForTier, onIdle, TIERS } from '@/lib/perf';

/**
 * The multi-hazard dashboard.
 *
 * Tayari used to open on a map of eight river basins, which answered "is the
 * Shabelle about to flood?" and nothing else. It now opens on a location and
 * asks the question people actually have: what threatens where I am, and what
 * should I do about it?
 *
 * The eight calibrated basins have not gone anywhere — they live at /basins and
 * remain the more trustworthy answer for the places they cover.
 */
export default function HazardDashboard() {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const maplibreRef = useRef(null);
  const eventMarkers = useRef([]);
  const locationMarker = useRef(null);
  const resizeObserverRef = useRef(null);
  const mapInitStarted = useRef(false);
  const mapTier = useRef(TIERS.HIGH);
  // Monotonic token so a slow profile response cannot overwrite a newer one.
  const profileId = useRef(0);

  const [location, setLocation] = useState(null);
  const [profile, setProfile] = useState(null);
  const [selected, setSelected] = useState(null);
  const [events, setEvents] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [mapReady, setMapReady] = useState(false);
  const [deferMap, setDeferMap] = useState(false);

  const { notify } = useToast();

  // ── Location → profile ──────────────────────────────────────────────────

  const loadProfile = useCallback(
    async (target) => {
      const id = ++profileId.current;
      setLoading(true);
      setError(null);
      try {
        // Name the coordinate here rather than server-side: the free
        // reverse-geocoder is licensed for browsers only. Run alongside the
        // assessment rather than before it — it is a label, and it must never
        // delay the hazard data or fail the request.
        let named = target;
        if (!target.name) {
          const [data, place] = await Promise.all([
            fetchHazardProfile(target),
            reverseGeocode(target.latitude, target.longitude),
          ]);
          if (id !== profileId.current) return;
          named = place ? { ...target, ...place } : target;
          setProfile(data);
          setSelected(null);
          const resolved = { ...named, ...data.location, ...(place || {}) };
          setLocation(resolved);
          saveLocation(resolved);
          return;
        }

        const data = await fetchHazardProfile(target);
        if (id !== profileId.current) return;
        setProfile(data);
        setSelected(null);
        const resolved = { ...target, ...data.location, name: target.name };
        setLocation(resolved);
        saveLocation(resolved);
      } catch (e) {
        if (id !== profileId.current) return;
        const message =
          e.status === 502
            ? 'The hazard data feeds are not responding. Please try again in a moment.'
            : 'Could not assess this location. Please check your connection and try again.';
        setError(message);
        notify({ type: 'error', title: 'Assessment failed', message });
      } finally {
        if (id === profileId.current) setLoading(false);
      }
    },
    [notify]
  );

  const handleSelectLocation = useCallback(
    (place) => {
      setLocation(place);
      setProfile(null);
      loadProfile(place);
      if (mapInstance.current) {
        mapInstance.current.flyTo({
          center: [place.longitude, place.latitude],
          zoom: 7,
          duration: 1400,
          essential: true,
        });
      }
    },
    [loadProfile]
  );

  // Restore the last place on load. No automatic geolocation prompt: a
  // permission dialog before the app has shown what it is for gets refused, and
  // a refusal is remembered by the browser far longer than the visit.
  useEffect(() => {
    const saved = loadLocation();
    if (saved) {
      // Reading localStorage is exactly the "synchronize with an external
      // system" case the rule exists to allow; it just cannot see that from
      // here. Setting the location before the profile arrives means the bar
      // shows the place name immediately rather than after the round-trip.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLocation(saved);
      loadProfile(saved);
    }
  }, [loadProfile]);

  // Live worldwide events for the map. Non-fatal — the map degrades to no pins.
  useEffect(() => {
    fetchLiveEvents({ minMagnitude: 4.5, days: 7 })
      .then(setEvents)
      .catch(() => setEvents(null));
  }, []);

  // ── Map ─────────────────────────────────────────────────────────────────

  const initMap = useCallback(async () => {
    if (mapInitStarted.current || mapInstance.current || !mapRef.current) return;
    mapInitStarted.current = true;
    setDeferMap(false);

    try {
      const maplibregl = await loadMapLibrary();
      maplibreRef.current = maplibregl;
      if (!mapRef.current) {
        mapInitStarted.current = false;
        return;
      }

      const saved = loadLocation();
      const map = new maplibregl.Map({
        container: mapRef.current,
        style: MAP_STYLE_URL,
        center: saved ? [saved.longitude, saved.latitude] : [20, 15],
        zoom: saved ? 6 : 1.4,
        attributionControl: true,
        cooperativeGestures: true,
        pitchWithRotate: false,
        dragRotate: false,
        maxPitch: 0,
        failIfMajorPerformanceCaveat: false,
        trackResize: true,
        ...mapOptionsForTier(mapTier.current),
      });

      map.addControl(new maplibregl.NavigationControl(), 'bottom-right');
      map.once('load', () => setMapReady(true));
      mapInstance.current = map;

      // The side panel changes the container width; MapLibre does not notice on
      // its own and the view drifts toward a corner until told to resize.
      let frame;
      const observer = new ResizeObserver(() => {
        if (frame) cancelAnimationFrame(frame);
        frame = requestAnimationFrame(() => map.resize());
      });
      observer.observe(mapRef.current);
      resizeObserverRef.current = observer;
    } catch (e) {
      console.error('Failed to initialize map:', e);
      mapInitStarted.current = false;
    }
  }, []);

  useEffect(() => {
    const tier = getDeviceTier();
    mapTier.current = tier;
    if (tier === TIERS.LOW) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDeferMap(true);
      return;
    }
    return onIdle(() => initMap(), tier === TIERS.HIGH ? 800 : 2000);
  }, [initMap]);

  useEffect(
    () => () => {
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
        resizeObserverRef.current = null;
      }
      if (mapInstance.current) {
        mapInstance.current.remove();
        mapInstance.current = null;
      }
    },
    []
  );

  // Live event pins: earthquakes sized by magnitude, volcanoes as markers.
  useEffect(() => {
    if (!mapInstance.current || !mapReady || !events) return;
    const maplibregl = maplibreRef.current;
    if (!maplibregl) return;

    eventMarkers.current.forEach((m) => m.remove());
    eventMarkers.current = [];

    (events.earthquakes || []).forEach((quake) => {
      const magnitude = quake.magnitude || 0;
      // Area, not radius, scales with magnitude — a linear radius makes an M7
      // look only slightly worse than an M5, which is the opposite of true.
      const size = Math.max(8, Math.min(34, (magnitude - 3) * 7));
      const el = document.createElement('div');
      el.className = 'map-quake';
      el.style.width = `${size}px`;
      el.style.height = `${size}px`;
      el.title = quake.title;

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([quake.longitude, quake.latitude])
        .setPopup(
          new maplibregl.Popup({ offset: 10, closeButton: false }).setHTML(
            `<strong>${escapeHtml(quake.title)}</strong><br/>` +
              `<span style="color:#6b6558">${
                quake.depth_km != null ? `${quake.depth_km.toFixed(0)} km deep · ` : ''
              }${quake.occurred_at ? new Date(quake.occurred_at).toLocaleString() : ''}</span>`
          )
        )
        .addTo(mapInstance.current);
      eventMarkers.current.push(marker);
    });

    (events.volcanoes || []).forEach((volcano) => {
      const el = document.createElement('div');
      el.className = 'map-volcano';
      el.textContent = '🌋';
      el.title = volcano.title;

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([volcano.longitude, volcano.latitude])
        .setPopup(
          new maplibregl.Popup({ offset: 10, closeButton: false }).setHTML(
            `<strong>${escapeHtml(volcano.name)}</strong><br/>` +
              `<span style="color:#6b6558">${escapeHtml(volcano.status)}${
                volcano.country ? ` · ${escapeHtml(volcano.country)}` : ''
              }</span>`
          )
        )
        .addTo(mapInstance.current);
      eventMarkers.current.push(marker);
    });
  }, [events, mapReady]);

  // The pin for wherever the user is asking about.
  useEffect(() => {
    if (!mapInstance.current || !mapReady || !location) return;
    const maplibregl = maplibreRef.current;
    if (!maplibregl) return;

    if (locationMarker.current) locationMarker.current.remove();

    const el = document.createElement('div');
    el.className = 'map-you';
    el.style.background = profile ? RISK_COLORS[profile.overall_risk] : '#23211c';
    el.title = placeLabel(location);

    locationMarker.current = new maplibregl.Marker({ element: el })
      .setLngLat([location.longitude, location.latitude])
      .addTo(mapInstance.current);
  }, [location, profile, mapReady]);

  // Escape closes the open hazard, and on phones — where the detail is a
  // full-screen sheet — the page underneath must not scroll behind it.
  useEffect(() => {
    if (!selected) return;
    const onKey = (e) => e.key === 'Escape' && setSelected(null);
    document.addEventListener('keydown', onKey);
    const phone = window.matchMedia('(max-width: 768px)').matches;
    if (phone) document.body.classList.add('sheet-open');
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.classList.remove('sheet-open');
    };
  }, [selected]);

  // ── Render ──────────────────────────────────────────────────────────────
  //
  // No sign-in gate. The dashboard used to open on a welcome card asking people
  // to sign in or "continue as guest" — on every visit, because the choice was
  // never remembered — before showing anything at all. Every feature here works
  // signed out, so the first screen is now the one question that matters, and
  // sign-in waits in the header for the people who want it.

  const overall = profile?.overall_risk?.toLowerCase();
  const top = profile?.hazards?.[0];

  return (
    <div className="main-content dashboard">
      <section className="hazard-panel animate-fade-in" aria-label="Hazards at your location">
        <LocationBar location={location} onSelect={handleSelectLocation} busy={loading} />

        {!location && !loading && (
          <div className="hazard-empty">
            <h1 className="hazard-empty-title">What threatens where you are?</h1>
            <p className="hazard-empty-text">
              Tayari checks nine hazards — floods, earthquakes, tsunami, volcanoes, storms,
              heat, wildfire, drought and landslides — against live data, then tells you what
              to do about the ones that matter. Free, no account needed.
            </p>
            <p className="hazard-empty-hint">Or try one of these:</p>
            <div className="example-places">
              {EXAMPLE_PLACES.map((place) => (
                <button
                  key={place.name}
                  type="button"
                  className="chip"
                  onClick={() => handleSelectLocation(place)}
                >
                  {place.name}
                </button>
              ))}
            </div>
          </div>
        )}

        {loading && !profile && (
          <div className="hazard-skeleton" aria-busy="true" aria-live="polite">
            <span className="visually-hidden">Checking nine hazards…</span>
            <div className="skeleton skeleton--banner" />
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="skeleton skeleton--card" />
            ))}
          </div>
        )}

        {error && !loading && (
          <div className="notice notice--error" role="alert">
            <p>{error}</p>
            {location && (
              <button
                type="button"
                className="btn btn-sm"
                style={{ marginTop: 8 }}
                onClick={() => loadProfile(location)}
              >
                Try again
              </button>
            )}
          </div>
        )}

        {profile && (
          <>
            <div
              className={`hazard-summary hazard-summary--${overall}`}
              role="status"
              aria-live="polite"
            >
              <div className="hazard-summary-top">
                <span className="hazard-summary-level">
                  {RISK_WORDS[profile.overall_risk] || profile.overall_risk}
                </span>
                {loading && <span className="hazard-summary-busy">Updating…</span>}
              </div>
              <p className="hazard-summary-headline">{profile.headline}</p>
              {top && top.risk_level !== 'LOW' && (
                <button
                  type="button"
                  className="btn btn-sm hazard-summary-cta"
                  onClick={() => setSelected(top)}
                >
                  What to do about {hazardMeta(top.hazard).short.toLowerCase()} →
                </button>
              )}
              {profile.partial && (
                <p className="hazard-summary-note">
                  Some data feeds did not respond, so a hazard may be missing.
                </p>
              )}
            </div>

            <h2 className="hazard-list-title">
              {profile.hazards.length} hazards checked · tap one for what to do
            </h2>
            <div className="hazard-list">
              {profile.hazards.map((risk) => (
                <HazardCard
                  key={risk.hazard}
                  risk={risk}
                  active={selected?.hazard === risk.hazard}
                  onSelect={setSelected}
                />
              ))}
            </div>

            {profile.screened_out.length > 0 && (
              <p className="hazard-screened">
                Not relevant here:{' '}
                {profile.screened_out.map((h) => hazardMeta(h).short).join(', ')}. Tayari
                checked and found no physical basis for these at this location.
              </p>
            )}
          </>
        )}
      </section>

      <div className="map-container" aria-label="Map of live earthquakes and volcanoes">
        <div ref={mapRef} style={{ position: 'absolute', inset: 0, width: '100%' }} />

        {!mapReady && (
          <div className="map-placeholder">
            {deferMap ? (
              <div className="map-placeholder-inner">
                <div className="map-placeholder-icon" aria-hidden="true">🗺️</div>
                <p className="map-placeholder-text">
                  The interactive map uses about 1&nbsp;MB of data.
                </p>
                <button className="btn btn-primary btn-sm" onClick={initMap}>
                  Load map
                </button>
              </div>
            ) : (
              <div className="map-placeholder-inner">
                <div className="spinner" />
                <span className="map-placeholder-text">Loading map…</span>
              </div>
            )}
          </div>
        )}
      </div>

      {selected && profile && (
        <div
          className="side-panel"
          role="dialog"
          aria-modal="false"
          aria-label={`${hazardMeta(selected.hazard).label} details`}
        >
          <HazardDetail
            risk={selected}
            location={{ ...profile.location, languages: profile.languages }}
            onClose={() => setSelected(null)}
          />
        </div>
      )}
    </div>
  );
}

// Plain words for the overall level. A bare "LOW" badge reads as a label, not
// an answer; the banner should say the answer.
const RISK_WORDS = {
  LOW: 'All clear for now',
  MODERATE: 'Stay alert',
  HIGH: 'Take action',
  EXTREME: 'Act now — danger',
};

// One-tap starting points for someone who just wants to see what this does,
// spread across the hazards and the regions Tayari was built for.
const EXAMPLE_PLACES = [
  { name: 'Beledweyne', country: 'Somalia', country_code: 'so', latitude: 4.74, longitude: 45.2 },
  { name: 'Nairobi', country: 'Kenya', country_code: 'ke', latitude: -1.2864, longitude: 36.8172 },
  { name: 'Jakarta', country: 'Indonesia', country_code: 'id', latitude: -6.2088, longitude: 106.8456 },
  { name: 'Manila', country: 'Philippines', country_code: 'ph', latitude: 14.5995, longitude: 120.9842 },
  { name: 'Naples', country: 'Italy', country_code: 'it', latitude: 40.8518, longitude: 14.2681 },
];

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
