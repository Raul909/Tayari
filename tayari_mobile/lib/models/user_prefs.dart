// The owner's personal choices, stored on-device.
//
// These drive what the app shows by default: which audience the advisories are
// written for, which language they arrive in, and which basin matters most to
// this phone's owner. Mirrors the roles/languages offered by the web dashboard
// and the backend enums so the same choice means the same thing everywhere.

class RoleOption {
  final String value;
  final String label;
  const RoleOption(this.value, this.label);
}

class LanguageOption {
  final String value;
  final String label;
  const LanguageOption(this.value, this.label);
}

/// Canonical audience roles — must match backend UserRole values.
const kRoleOptions = <RoleOption>[
  RoleOption('general', 'General public'),
  RoleOption('farmer', 'Farmer'),
  RoleOption('pastoralist', 'Pastoralist'),
  RoleOption('county_officer', 'County officer'),
  RoleOption('community_leader', 'Community leader'),
];

/// Canonical languages — must match backend Language values.
const kLanguageOptions = <LanguageOption>[
  LanguageOption('en', 'English'),
  LanguageOption('so', 'Somali'),
  LanguageOption('sw', 'Swahili'),
  LanguageOption('am', 'Amharic'),
  LanguageOption('om', 'Oromo'),
  LanguageOption('ar', 'Arabic'),
  LanguageOption('aa', 'Afar'),
  LanguageOption('din', 'Dinka'),
  LanguageOption('dsh', 'Daasanach'),
  LanguageOption('luy', 'Luhya'),
  LanguageOption('tuv', 'Turkana'),
];

/// Locally relevant languages per basin (mother-tongue first), mirroring
/// `languages` in the backend's basins.json. Used to show only the languages
/// that actually work on the ground for each basin — e.g. the lower Omo speaks
/// Daasanach, not Oromo. Falls back to English for any unlisted basin.
const kBasinLanguages = <String, List<String>>{
  'shabelle': ['so', 'en'],
  'juba': ['so', 'en'],
  'tana': ['sw', 'en'],
  'nzoia': ['luy', 'sw', 'en'],
  'awash': ['aa', 'am', 'en'],
  'white_nile': ['din', 'ar', 'en'],
  'blue_nile': ['ar', 'en'],
  'omo': ['dsh', 'am', 'en'],
};

List<LanguageOption> languageOptionsForBasin(String? basinId) {
  final codes = kBasinLanguages[basinId] ?? const ['en'];
  return [
    for (final code in codes)
      kLanguageOptions.firstWhere(
        (o) => o.value == code,
        orElse: () => LanguageOption(code, code),
      ),
  ];
}

class UserPrefs {
  final String role;
  final String language;

  /// The basin this owner cares about most; pinned to the top of the list.
  /// Null until the owner picks one.
  final String? homeBasinId;

  const UserPrefs({
    required this.role,
    required this.language,
    this.homeBasinId,
  });

  static const defaults = UserPrefs(role: 'general', language: 'en');

  UserPrefs copyWith({
    String? role,
    String? language,
    String? homeBasinId,
    bool clearHome = false,
  }) {
    return UserPrefs(
      role: role ?? this.role,
      language: language ?? this.language,
      homeBasinId: clearHome ? null : (homeBasinId ?? this.homeBasinId),
    );
  }

  static String roleLabel(String value) => kRoleOptions
      .firstWhere((o) => o.value == value, orElse: () => kRoleOptions.first)
      .label;

  static String languageLabel(String value) => kLanguageOptions
      .firstWhere((o) => o.value == value, orElse: () => kLanguageOptions.first)
      .label;
}
