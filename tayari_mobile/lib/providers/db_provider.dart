import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';
import 'package:path_provider/path_provider.dart';

import '../models/basin.dart';
import '../models/forecast.dart';
import '../services/api_client.dart';
import '../services/sync_service.dart';

// 1. Isar DB Initialization Provider
final isarProvider = FutureProvider<Isar>((ref) async {
  final dir = await getApplicationDocumentsDirectory();
  return await Isar.open(
    [BasinSchema, ForecastSchema],
    directory: dir.path,
  );
});

// 2. ApiClient Provider
final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient();
});

// 3. SyncService Provider
final syncServiceProvider = FutureProvider<SyncService>((ref) async {
  final isar = await ref.watch(isarProvider.future);
  final apiClient = ref.watch(apiClientProvider);
  return SyncService(apiClient, isar);
});
