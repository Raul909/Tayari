import 'package:dio/dio.dart';

/// The deployed API, served through Tayari's edge gateway on Cloudflare.
///
/// The gateway answers from cache for places people have recently checked,
/// and keeps answering while the free Render instance behind it is asleep —
/// the half-minute cold start used to land on whoever opened the app first.
const kEdgeBase = 'https://tayari.pages.dev';

/// The API's own address, used only when the gateway itself fails.
const kDirectBase = 'https://tayari-api.onrender.com';

/// Retries a request against Render directly when the edge gateway fails.
///
/// The gateway runs on Cloudflare's free plan, which has a daily request
/// allowance; it must never be the reason the app cannot reach the API. A
/// failure *of Render* reported by the gateway carries an `x-tayari-edge`
/// header and is not retried — Render is down either way, and the gateway has
/// already served a saved answer if it had one.
class EdgeFallback extends Interceptor {
  EdgeFallback(this._dio);

  final Dio _dio;

  bool _gatewayFailed(DioException err) {
    final response = err.response;
    if (response == null) {
      return err.type == DioExceptionType.connectionError ||
          err.type == DioExceptionType.connectionTimeout;
    }
    final status = response.statusCode ?? 0;
    return status >= 429 && response.headers.value('x-tayari-edge') == null;
  }

  @override
  Future<void> onError(DioException err, ErrorInterceptorHandler handler) async {
    final options = err.requestOptions;
    final viaEdge = options.uri.toString().startsWith(kEdgeBase);
    if (!viaEdge || options.extra['edgeFallback'] == true || !_gatewayFailed(err)) {
      return handler.next(err);
    }
    try {
      final data = options.data;
      final retry = options.copyWith(
        baseUrl: options.baseUrl.replaceFirst(kEdgeBase, kDirectBase),
        path: options.path.replaceFirst(kEdgeBase, kDirectBase),
        // A multipart body can only be sent once; send a fresh copy.
        data: data is FormData ? data.clone() : data,
        extra: {...options.extra, 'edgeFallback': true},
      );
      handler.resolve(await _dio.fetch(retry));
    } on DioException catch (e) {
      handler.next(e);
    }
  }
}
