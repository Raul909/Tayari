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
  nzoia: {
    id: 'nzoia',
    name: 'Nzoia Basin (Budalangi)',
    river: 'Nzoia River',
    country: 'Kenya',
    lat: 0.10,
    lng: 34.05,
    zoom: 9,
  },
  awash: {
    id: 'awash',
    name: 'Awash Basin (Dubti)',
    river: 'Awash River',
    country: 'Ethiopia',
    lat: 11.73,
    lng: 41.08,
    zoom: 9,
  },
  white_nile: {
    id: 'white_nile',
    name: 'White Nile Basin (Bor)',
    river: 'White Nile',
    country: 'South Sudan',
    lat: 6.21,
    lng: 31.56,
    zoom: 9,
  },
  blue_nile: {
    id: 'blue_nile',
    name: 'Blue Nile Basin (Khartoum)',
    river: 'Blue Nile',
    country: 'Sudan',
    lat: 15.55,
    lng: 32.53,
    zoom: 9,
  },
  omo: {
    id: 'omo',
    name: 'Omo Basin (Omorate)',
    river: 'Omo River',
    country: 'Ethiopia',
    lat: 4.80,
    lng: 35.96,
    zoom: 9,
  },
};

export const MAP_CENTER = { lat: 2.0, lng: 42.0, zoom: 5 };

export const RISK_COLORS = {
  LOW: '#3F7D53',
  MODERATE: '#B0812C',
  HIGH: '#C0432B',
  EXTREME: '#83291A',
};

export const RISK_BG_COLORS = {
  LOW: 'rgba(63, 125, 83, 0.12)',
  MODERATE: 'rgba(176, 129, 44, 0.14)',
  HIGH: 'rgba(192, 67, 43, 0.12)',
  EXTREME: 'rgba(131, 41, 26, 0.14)',
};

export const ROLES = [
  { value: 'general', label: 'General Public' },
  { value: 'farmer', label: 'Farmer' },
  { value: 'pastoralist', label: 'Pastoralist' },
  { value: 'county_officer', label: 'County Officer' },
  { value: 'community_leader', label: 'Community Leader' },
];

export const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'so', label: 'Somali' },
  { value: 'sw', label: 'Swahili' },
  { value: 'am', label: 'Amharic' },
  { value: 'om', label: 'Oromo' },
];

export const REPORT_STATUSES = [
  { value: 'water_rising', label: 'Water rising', color: '#B0812C' },
  { value: 'road_flooded', label: 'Road flooded', color: '#C0432B' },
  { value: 'evacuating', label: 'Evacuating', color: '#83291A' },
  { value: 'all_clear', label: 'All clear', color: '#3F7D53' },
];
