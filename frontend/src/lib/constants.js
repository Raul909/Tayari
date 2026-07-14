/**
 * Constants for the Tayari app.
 */

export const BASINS = {
  shabelle: {
    id: 'shabelle',
    name: 'Shabelle Basin (Beledweyne)',
    river: 'Shabelle River',
    country: 'Somalia',
    lat: 4.74,
    lng: 45.20,
    zoom: 9,
  },
  juba: {
    id: 'juba',
    name: 'Juba Basin (Luuq)',
    river: 'Juba River',
    country: 'Somalia',
    lat: 3.80,
    lng: 42.54,
    zoom: 9,
  },
  tana: {
    id: 'tana',
    name: 'Tana Basin (Garsen)',
    river: 'Tana River',
    country: 'Kenya',
    lat: -2.27,
    lng: 40.12,
    zoom: 9,
  },
};

export const MAP_CENTER = { lat: 2.0, lng: 42.0, zoom: 5 };

export const RISK_COLORS = {
  LOW: '#22C55E',
  MODERATE: '#EAB308',
  HIGH: '#EF4444',
  EXTREME: '#991B1B',
};

export const RISK_BG_COLORS = {
  LOW: 'rgba(34, 197, 94, 0.15)',
  MODERATE: 'rgba(234, 179, 8, 0.15)',
  HIGH: 'rgba(239, 68, 68, 0.15)',
  EXTREME: 'rgba(153, 27, 27, 0.2)',
};

export const ROLES = [
  { value: 'general', label: 'General Public' },
  { value: 'farmer', label: 'Farmer' },
  { value: 'pastoralist', label: 'Pastoralist' },
  { value: 'county_officer', label: 'County Officer' },
  { value: 'community_leader', label: 'Community Leader' },
];

export const LANGUAGES = [
  { value: 'en', label: 'English', flag: '🇬🇧' },
  { value: 'so', label: 'Somali', flag: '🇸🇴' },
  { value: 'sw', label: 'Swahili', flag: '🇰🇪' },
  { value: 'am', label: 'Amharic', flag: '🇪🇹' },
  { value: 'om', label: 'Oromo', flag: '🇪🇹' },
];

export const REPORT_STATUSES = [
  { value: 'water_rising', label: '🌊 Water Rising', color: '#EAB308' },
  { value: 'road_flooded', label: '🚧 Road Flooded', color: '#EF4444' },
  { value: 'evacuating', label: '🏃 Evacuating', color: '#991B1B' },
  { value: 'all_clear', label: '✅ All Clear', color: '#22C55E' },
];
