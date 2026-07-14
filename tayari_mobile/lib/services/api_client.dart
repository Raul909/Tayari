import 'package:dio/dio.dart';

class ApiClient {
  final Dio _dio;

  ApiClient() : _dio = Dio(BaseOptions(
    // In emulator, 10.0.2.2 points to localhost. Use actual IP for physical devices.
    baseUrl: 'http://127.0.0.1:8000/api', 
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 10),
  )) {
    _dio.interceptors.add(LogInterceptor(responseBody: true));
  }

  Future<List<dynamic>> getBasins() async {
    final response = await _dio.get('/basins');
    return response.data;
  }

  Future<Map<String, dynamic>> getForecast(String basinId, String role, String language) async {
    final response = await _dio.get(
      '/forecasts/$basinId',
      queryParameters: {
        'role': role,
        'language': language,
      },
    );
    return response.data;
  }
}
