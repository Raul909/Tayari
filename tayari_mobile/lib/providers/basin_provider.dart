import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';

import '../models/basin.dart';
import '../models/forecast.dart';
import 'db_provider.dart';

// Stream of Basins from the local Isar Database (Offline-First)
final basinsStreamProvider = StreamProvider<List<Basin>>((ref) async* {
  final isar = await ref.watch(isarProvider.future);
  
  // Trigger a background network sync (doesn't block the stream)
  ref.read(syncServiceProvider.future).then((syncService) {
    syncService.syncBasins();
  });

  // Yield the live stream from Isar
  yield* isar.basins.where().watch(fireImmediately: true);
});

// Stream of a specific Forecast from Isar
final forecastStreamProvider = StreamProvider.family<Forecast?, String>((ref, basinId) async* {
  final isar = await ref.watch(isarProvider.future);
  
  yield* isar.forecasts.where().basinIdEqualTo(basinId).watch(fireImmediately: true).map((list) {
    return list.isNotEmpty ? list.first : null;
  });
});
