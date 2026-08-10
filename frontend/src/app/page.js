'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import 'maplibre-gl/dist/maplibre-gl.css';
import HazardCard from '@/components/HazardCard';
import HazardDetail from '@/components/HazardDetail';
import LocationBar from '@/components/LocationBar';
import OnboardingSplash from '@/components/OnboardingSplash';
import { useToast } from '@/components/Toast';
import { useAuth } from '@/lib/auth';
import { MAP_STYLE_URL, RISK_COLORS } from '@/lib/constants';
import {
  fetchHazardProfile,
  fetchLiveEvents,
  hazardMeta,
  loadLocation,
  placeLabel,
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

  const { user, loading: authLoading, isGuest, setGuest } = useAuth();
  const { notify } = useToast();

  // ── Location → profile ──────────────────────────────────────────────────

  const loadProfile = useCallback(
    async (target) => {
      const id = ++profileId.current;
      setLoading(true);
      setError(null);
      try {
        const data = await fetchHazardProfile(target);
        if (id !== profileId.current) return;
        setProfile(data);
        setSelected(null);
        // The API resolves the place name and country; keeping them means a
        // reload shows "Kathmandu, Nepal" rather than a pair of numbers.
        const resolved = { ...target, ...data.location };
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
    if (authLoading || !(user || isGuest)) return;
    const tier = getDeviceTier();
    mapTier.current = tier;
    if (tier === TIERS.LOW) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDeferMap(true);
      return;
    }
    return onIdle(() => initMap(), tier === TIERS.HIGH ? 800 : 2000);
  }, [authLoading, user, isGuest, initMap]);

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

  // ── Render ──────────────────────────────────────────────────────────────

  if (authLoading) {
    return (
      <div className="loading-container" style={{ minHeight: '100vh' }}>
        <div className="spinner" />
        <span>Loading Tayari…</span>
      </div>
    );
  }

  if (!user && !isGuest) {
    return <OnboardingSplash onGuestContinue={() => setGuest(true)} />;
  }

  return (
    <div className="main-content">
      <div className="map-container">
        <div
          ref={mapRef}
          style={{ position: 'absolute', inset: 0, width: '100%' }}
        />

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

      <div className="hazard-panel animate-fade-in">
          <LocationBar
            location={location}
            onSelect={handleSelectLocation}
            busy={loading}
          />

          {!location && !loading && (
            <div className="hazard-empty">
              <h1 className="hazard-empty-title">What threatens where you are?</h1>
              <p className="hazard-empty-text">
                Tayari checks nine hazards — flooding, earthquakes, tsunami, volcanic activity,
                storms, heat, wildfire, drought and landslides — against live data from USGS,
                the Smithsonian Global Volcanism Program, Copernicus and Open-Meteo, then
                explains what to do about the ones that matter.
              </p>
              <p className="hazard-empty-text">
                Share your location or search for a place to begin.
              </p>
            </div>
          )}

          {loading && !profile && (
            <div className="loading-container">
              <div className="spinner" />
              <span style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                Checking nine hazards…
              </span>
            </div>
          )}

          {error && !loading && (
            <div className="notice notice--error" role="alert">
              {error}
            </div>
          )}

          {profile && (
            <>
              <div className="hazard-summary">
                <span
                  className={`risk-badge risk-badge--${profile.overall_risk.toLowerCase()}`}
                >
                  {profile.overall_risk}
                </span>
                <p className="hazard-summary-headline">{profile.headline}</p>
                {profile.partial && (
                  <p className="hazard-summary-note">
                    One or more data feeds did not respond, so some hazards may be missing.
                  </p>
                )}
              </div>

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
      </div>

      {selected && profile && (
        <div className="side-panel">
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

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
