import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api_client.dart';

/// Client for the location-based multi-hazard API — the same endpoints the web
/// dashboard uses, so a place reads the same on a phone as on a laptop.
///
/// Kept apart from [ApiClient] because the timeouts differ on purpose: the
/// basin endpoints answer from the server's cache, while a hazard profile for a
/// place nobody has asked about yet gathers seven live feeds, and a Render cold
/// start can add half a minute on top. Ten seconds would fail exactly the first
/// request someone makes.
class HazardApi {
  final Dio _dio;

  HazardApi()
      : _dio = Dio(BaseOptions(
          baseUrl: '${ApiClient.assetBaseUrl}/api',
          connectTimeout: const Duration(seconds: 20),
          receiveTimeout: const Duration(seconds: 45),
        ));

  /// The full multi-hazard profile for a coordinate.
  Future<Map<String, dynamic>> profile(Place place) async {
    final res = await _dio.get('/hazards', queryParameters: place.query);
    return Map<String, dynamic>.from(res.data as Map);
  }

  /// A plain-language advisory for one hazard, in one language, for one role.
  Future<Map<String, dynamic>> advisory(
    String hazard,
    Place place, {
    String role = 'general',
    String language = 'en',
  }) async {
    final res = await _dio.get('/hazards/$hazard/advisory', queryParameters: {
      ...place.query,
      'role': role,
      'language': language,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  /// Search for a place by name.
  Future<List<Place>> search(String query) async {
    final res = await _dio.get('/places/search', queryParameters: {'q': query, 'count': 6});
    return [
      for (final p in (res.data as List))
        Place.fromJson(Map<String, dynamic>.from(p as Map)),
    ];
  }

  /// A sentence for someone who is not a developer.
  static String describeError(Object e) {
    if (e is DioException) {
      switch (e.type) {
        case DioExceptionType.connectionTimeout:
        case DioExceptionType.receiveTimeout:
          return 'The server is taking a while to wake up. Try again in a moment.';
        case DioExceptionType.connectionError:
          return 'No connection. Showing the last result saved on this phone.';
        default:
          final code = e.response?.statusCode;
          if (code == 502 || code == 503) {
            return 'The hazard data feeds are not responding. Try again shortly.';
          }
      }
    }
    return 'Could not check this place. Try again.';
  }
}

/// A place someone has chosen to check.
class Place {
  final double latitude;
  final double longitude;
  final String? name;
  final String? admin1;
  final String? country;
  final String? countryCode;

  const Place({
    required this.latitude,
    required this.longitude,
    this.name,
    this.admin1,
    this.country,
    this.countryCode,
  });

  factory Place.fromJson(Map<String, dynamic> j) => Place(
        latitude: (j['latitude'] as num).toDouble(),
        longitude: (j['longitude'] as num).toDouble(),
        name: j['name'] as String?,
        admin1: j['admin1'] as String?,
        country: j['country'] as String?,
        countryCode: j['country_code'] as String?,
      );

  Map<String, dynamic> toJson() => {
        'latitude': latitude,
        'longitude': longitude,
        'name': ?name,
        'admin1': ?admin1,
        'country': ?country,
        'country_code': ?countryCode,
      };

  Map<String, dynamic> get query => {
        'lat': latitude,
        'lon': longitude,
        'name': ?name,
        'country': ?country,
        'country_code': ?countryCode,
      };

  /// "Nairobi, Kenya", without the "Kathmandu, Kathmandu" duplication that
  /// geocoders produce, falling back to coordinates.
  String get label {
    final parts = <String>[];
    for (final p in [name, admin1, country]) {
      if (p != null && p.isNotEmpty && !parts.contains(p)) parts.add(p);
    }
    if (parts.isNotEmpty) return parts.join(', ');
    return '${latitude.toStringAsFixed(3)}, ${longitude.toStringAsFixed(3)}';
  }

  /// Merge in the server's resolved name, keeping anything we already had.
  Place withServerLocation(Map<String, dynamic>? loc) {
    if (loc == null) return this;
    return Place(
      latitude: latitude,
      longitude: longitude,
      name: name ?? loc['name'] as String?,
      admin1: admin1 ?? loc['admin1'] as String?,
      country: country ?? loc['country'] as String?,
      countryCode: countryCode ?? loc['country_code'] as String?,
    );
  }
}

/// The last place checked and its profile, kept on the phone.
///
/// This app is meant for places where the signal comes and goes. Opening it to
/// a spinner — or an error — because the network dropped would hide a result
/// that was perfectly good an hour ago; so the last answer is shown at once,
/// with its age, and refreshed behind it.
class HazardCache {
  static const _kPlace = 'hazard_place';
  static const _kProfile = 'hazard_profile';
  static const _kSavedAt = 'hazard_saved_at';

  final SharedPreferences _prefs;
  HazardCache(this._prefs);

  Place? get place {
    final raw = _prefs.getString(_kPlace);
    if (raw == null) return null;
    try {
      return Place.fromJson(Map<String, dynamic>.from(jsonDecode(raw) as Map));
    } catch (_) {
      return null;
    }
  }

  Map<String, dynamic>? get profile {
    final raw = _prefs.getString(_kProfile);
    if (raw == null) return null;
    try {
      return Map<String, dynamic>.from(jsonDecode(raw) as Map);
    } catch (_) {
      return null;
    }
  }

  DateTime? get savedAt {
    final ms = _prefs.getInt(_kSavedAt);
    return ms == null ? null : DateTime.fromMillisecondsSinceEpoch(ms);
  }

  Future<void> savePlace(Place place) =>
      _prefs.setString(_kPlace, jsonEncode(place.toJson()));

  Future<void> saveProfile(Map<String, dynamic> profile) async {
    await _prefs.setString(_kProfile, jsonEncode(profile));
    await _prefs.setInt(_kSavedAt, DateTime.now().millisecondsSinceEpoch);
  }
}
