import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/user_prefs.dart';

/// Holds the SharedPreferences instance. Overridden in main() once the async
/// `SharedPreferences.getInstance()` has resolved, so the rest of the app can
/// read the owner's saved choices synchronously.
final sharedPrefsProvider = Provider<SharedPreferences>(
  (ref) => throw UnimplementedError(
    'sharedPrefsProvider must be overridden in main()',
  ),
);

/// The owner's on-device preferences. Changing role/language/home basin here
/// updates the UI immediately and persists to disk.
final userPrefsProvider =
    StateNotifierProvider<UserPrefsNotifier, UserPrefs>((ref) {
  return UserPrefsNotifier(ref.watch(sharedPrefsProvider));
});

class UserPrefsNotifier extends StateNotifier<UserPrefs> {
  final SharedPreferences _prefs;

  static const _kRole = 'pref_role';
  static const _kLang = 'pref_language';
  static const _kHome = 'pref_home_basin';

  UserPrefsNotifier(this._prefs) : super(_load(_prefs));

  static UserPrefs _load(SharedPreferences p) => UserPrefs(
        role: p.getString(_kRole) ?? UserPrefs.defaults.role,
        language: p.getString(_kLang) ?? UserPrefs.defaults.language,
        homeBasinId: p.getString(_kHome),
      );

  Future<void> setRole(String role) async {
    if (role == state.role) return;
    state = state.copyWith(role: role);
    await _prefs.setString(_kRole, role);
  }

  Future<void> setLanguage(String language) async {
    if (language == state.language) return;
    state = state.copyWith(language: language);
    await _prefs.setString(_kLang, language);
  }

  Future<void> setHomeBasin(String? basinId) async {
    state = state.copyWith(homeBasinId: basinId, clearHome: basinId == null);
    if (basinId == null) {
      await _prefs.remove(_kHome);
    } else {
      await _prefs.setString(_kHome, basinId);
    }
  }
}
