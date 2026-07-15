import 'dart:io' show File, Platform;
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart' show kIsWeb;

import '../models/report.dart';

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

  /// The host loopback address differs by platform: the Android emulator
  /// reaches the host machine at 10.0.2.2, everything else at 127.0.0.1.
  /// Override with --dart-define=API_BASE_URL=... for a real device/server.
  static String _resolveBaseUrl() {
    const override = String.fromEnvironment('API_BASE_URL');
    if (override.isNotEmpty) return override;
    if (!kIsWeb && Platform.isAndroid) return 'http://10.0.2.2:8000/api';
    return 'http://127.0.0.1:8000/api';
  }

  Future<List<dynamic>> getBasins() async {
    final response = await _dio.get('/basins');
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
}
