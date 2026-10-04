/// Labels and icons for the nine hazards, mirrored from the backend registry
/// (and the web app's `HAZARD_META`) so the first frame has them without a
/// request.
class HazardMeta {
  final String label;
  final String short;
  final String icon;
  const HazardMeta(this.label, this.short, this.icon);
}

const kHazardMeta = <String, HazardMeta>{
  'flood': HazardMeta('River flooding', 'Flood', '🌊'),
  'earthquake': HazardMeta('Earthquake', 'Quake', '🏚️'),
  'tsunami': HazardMeta('Tsunami', 'Tsunami', '🌀'),
  'volcano': HazardMeta('Volcanic activity', 'Volcano', '🌋'),
  'cyclone': HazardMeta('Cyclone & severe storm', 'Storm', '🌪️'),
  'extreme_heat': HazardMeta('Extreme heat', 'Heat', '🔥'),
  'wildfire': HazardMeta('Wildfire weather', 'Wildfire', '🔥'),
  'drought': HazardMeta('Drought', 'Drought', '🏜️'),
  'landslide': HazardMeta('Landslide', 'Landslide', '⛰️'),
};

HazardMeta hazardMeta(String hazard) =>
    kHazardMeta[hazard] ?? HazardMeta(hazard, hazard, '⚠️');

/// How fast a hazard arrives, in words someone can act on.
const kOnsetLabels = <String, String>{
  'instant': 'No warning possible',
  'minutes': 'Minutes',
  'hours': 'Hours',
  'days': 'Days',
  'seasons': 'Weeks to months',
};

/// The overall level as an answer rather than a label.
const kRiskWords = <String, String>{
  'LOW': 'All clear for now',
  'MODERATE': 'Stay alert',
  'HIGH': 'Take action',
  'EXTREME': 'Act now — danger',
};
