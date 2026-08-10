'use client';

import { useEffect, useRef, useState } from 'react';
import { detectLocation, placeLabel, searchPlaces } from '@/lib/hazards';

/**
 * Choosing a place: device location, or a name.
 *
 * Both paths are offered equally rather than leading with a permission prompt.
 * Geolocation is refused or unavailable often enough — blocked by policy, an
 * older device, a shared computer, someone checking on a relative's town rather
 * than their own — that treating search as the fallback would leave a lot of
 * people at a dead end.
 */
export default function LocationBar({ location, onSelect, busy }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [error, setError] = useState(null);
  const [open, setOpen] = useState(false);

  const containerRef = useRef(null);
  // Monotonic token so a slow search response cannot overwrite a newer one.
  const searchId = useRef(0);

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      // Clearing stale results as the query shrinks; nothing cascades because
      // both values are already empty on every subsequent pass.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setResults([]);
      setSearching(false);
      return;
    }

    // Debounced: the geocoder is a shared free service and a request per
    // keystroke is both slow for the user and rude to the upstream.
    const id = ++searchId.current;
    setSearching(true);
    const timer = setTimeout(async () => {
      try {
        const found = await searchPlaces(trimmed, { count: 6 });
        if (id === searchId.current) {
          setResults(found);
          setOpen(true);
        }
      } catch {
        if (id === searchId.current) setResults([]);
      } finally {
        if (id === searchId.current) setSearching(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  // Close the result list on an outside click, as a dropdown should.
  useEffect(() => {
    function handleClick(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  async function handleDetect() {
    setDetecting(true);
    setError(null);
    try {
      const coords = await detectLocation();
      onSelect({ latitude: coords.latitude, longitude: coords.longitude });
      setQuery('');
      setResults([]);
      setOpen(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setDetecting(false);
    }
  }

  function handlePick(place) {
    onSelect({
      latitude: place.latitude,
      longitude: place.longitude,
      name: place.name,
      country: place.country,
      country_code: place.country_code,
      admin1: place.admin1,
    });
    setQuery('');
    setResults([]);
    setOpen(false);
    setError(null);
  }

  return (
    <div className="location-bar" ref={containerRef}>
      <div className="location-bar-row">
        <div className="location-search">
          <input
            type="search"
            className="form-input location-search-input"
            placeholder="Search any town, city or district…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => results.length && setOpen(true)}
            aria-label="Search for a place"
            autoComplete="off"
          />
          {searching && <span className="location-search-spinner" aria-hidden="true" />}

          {open && results.length > 0 && (
            <ul className="location-results" role="listbox">
              {results.map((place) => (
                <li key={`${place.latitude},${place.longitude},${place.name}`}>
                  <button type="button" onClick={() => handlePick(place)}>
                    <span className="location-result-name">{place.name}</span>
                    <span className="location-result-meta">
                      {[place.admin1, place.country].filter(Boolean).join(', ')}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <button
          type="button"
          className="btn btn-ghost location-detect"
          onClick={handleDetect}
          disabled={detecting || busy}
        >
          {detecting ? 'Locating…' : '📍 Use my location'}
        </button>
      </div>

      {location && (
        <div className="location-current">
          <strong>{placeLabel(location)}</strong>
          {busy && <span className="location-current-busy">Assessing hazards…</span>}
        </div>
      )}

      {error && (
        <div className="notice notice--error location-error" role="alert">
          {error}
        </div>
      )}
    </div>
  );
}
