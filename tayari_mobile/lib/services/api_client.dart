import 'dart:io' show File, Platform;
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart' show kIsWeb, kReleaseMode;

import '../models/report.dart';
import 'groq_service.dart';

/// Maps the app's human-readable report status to the backend enum value
/// (backend ReportStatus: water_rising | road_flooded | evacuating | all_clear).
const _statusToApi = {
  'Water rising': 'water_rising',
  'Road flooded': 'road_flooded',
  'Evacuating': 'evacuating',
  'All clear': 'all_clear',
};

class ApiClient {
  final Dio _dio;

  ApiClient() : _dio = Dio(BaseOptions(
    baseUrl: _resolveBaseUrl(),
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 10),
  )) {
    _dio.interceptors.add(LogInterceptor());
  }

  /// The deployed backend. Release builds (the distributed APK) always target
  /// this — an end user's phone has no local dev server to reach.
  static const _productionBaseUrl = 'https://tayari-api.onrender.com/api';

  /// Resolves the backend base URL:
  ///   1. An explicit `--dart-define=API_BASE_URL=...` always wins.
  ///   2. Release builds default to the deployed production backend.
  ///   3. Debug/profile builds default to the local dev server. The host
  ///      loopback differs by platform: the Android emulator reaches the host
  ///      machine at 10.0.2.2, everything else at 127.0.0.1.
  static String _resolveBaseUrl() {
    const override = String.fromEnvironment('API_BASE_URL');
    if (override.isNotEmpty) return override;
    if (kReleaseMode) return _productionBaseUrl;
    if (!kIsWeb && Platform.isAndroid) return 'http://10.0.2.2:8000/api';
    return 'http://127.0.0.1:8000/api';
  }

  /// Base URL for static assets (report photos) — API base without `/api`.
  static String get assetBaseUrl =>
      _resolveBaseUrl().replaceFirst(RegExp(r'/api$'), '');

  Future<List<dynamic>> getBasins() async {
    final response = await _dio.get('/basins');
    return response.data;
  }

  /// Fetch community reports (newest last), optionally for a single basin.
  Future<List<dynamic>> getReports({String? basinId, int limit = 100}) async {
    final response = await _dio.get('/reports', queryParameters: {
      'basin_id': ?basinId,
      'limit': limit,
    });
    return response.data;
  }

  /// Attach advice to a community report; returns the updated report.
  Future<Map<String, dynamic>> postAdvice(
    int reportId, {
    required String message,
    String? authorName,
    String? authorRole,
  }) async {
    final response = await _dio.post('/reports/$reportId/advice', data: {
      'message': message,
      if (authorName != null && authorName.isNotEmpty) 'author_name': authorName,
      if (authorRole != null && authorRole.isNotEmpty) 'author_role': authorRole,
    });
    return response.data;
  }

  Future<Map<String, dynamic>> getForecast(
      String basinId, String role, String language) async {
    final response = await _dio.get(
      '/forecasts/$basinId',
      queryParameters: {
        'role': role,
        'language': language,
      },
    );
    return response.data;
  }

  /// Upload a queued community report to the backend, including the compressed
  /// photo as a multipart file. Falls back to the JSON-only endpoint if the
  /// multipart upload fails (e.g. older backend without /reports/upload).
  Future<void> uploadReport(CommunityReport report) async {
    final apiStatus = _statusToApi[report.status] ?? 'water_rising';

    // Try the multipart endpoint first (sends the actual photo binary).
    try {
      final formData = FormData.fromMap({
        'basin_id': report.basinId,
        'status': apiStatus,
        'latitude': report.latitude,
        'longitude': report.longitude,
      });

      // Attach the compressed photo if the file exists on disk.
      final photoFile = File(report.compressedPhotoPath);
      if (await photoFile.exists()) {
        formData.files.add(MapEntry(
          'photo',
          await MultipartFile.fromFile(
            report.compressedPhotoPath,
            filename: 'report_${report.id}.jpg',
          ),
        ));
      }

      await _dio.post('/reports/upload', data: formData);
      return; // Success — done.
    } catch (_) {
      // Multipart failed; fall back to JSON-only endpoint below.
    }

    // Fallback: JSON-only (no photo binary, matches the original endpoint).
    await _dio.post('/reports', data: {
      'basin_id': report.basinId,
      'status': apiStatus,
      'latitude': report.latitude,
      'longitude': report.longitude,
    });
  }

  /// Fetch the AI-generated advisory for a basin from the backend.
  /// Falls back to direct Groq API call if the backend is unreachable.
  Future<Map<String, dynamic>?> getAdvisory(
      String basinId, String role, String language) async {
    try {
      final response = await _dio.get(
        '/advisory/$basinId',
        queryParameters: {'role': role, 'language': language},
      );
      return response.data;
    } catch (e) {
      // Backend unreachable — try direct Groq API as fallback
      return _getAdvisoryViaGroq(basinId, role, language);
    }
  }

  /// Direct Groq API fallback for advisory generation.
  Future<Map<String, dynamic>?> _getAdvisoryViaGroq(
      String basinId, String role, String language) async {
    if (!GroqService.isAvailable) return null;

    final groq = GroqService();
    final advisory = await groq.generateAdvisory(
      basinName: basinId,
      riverName: basinId,
      country: 'East Africa',
      riskLevel: 'MODERATE',
      probability: 0.5,
      populationAtRisk: 5000,
      role: role,
      language: language,
    );

    if (advisory != null) {
      return {'advisory': advisory};
    }
    return null;
  }
}
