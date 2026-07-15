import 'package:flutter/foundation.dart';
import 'package:isar/isar.dart';
import '../models/basin.dart';
import '../models/forecast.dart';
import '../models/report.dart';
import 'api_client.dart';

class SyncService {
  final ApiClient _apiClient;
  final Isar _isar;

  SyncService(this._apiClient, this._isar);

  /// Fetch latest basins from FastAPI and upsert to local Isar DB
  Future<void> syncBasins() async {
    try {
      final data = await _apiClient.getBasins();

      final basins = data.map((json) {
        return Basin()
          ..basinId = json['id']
          ..name = json['name']
          ..river = json['river']
          ..country = json['country']
          ..latitude = (json['latitude'] as num).toDouble()
          ..longitude = (json['longitude'] as num).toDouble()
          ..currentDischarge = (json['current_discharge'] ?? 0).toDouble()
          ..currentRisk = json['current_risk'] ?? 'LOW'
          ..floodProbability = (json['flood_probability'] as num?)?.toDouble();
      }).toList();

      await _isar.writeTxn(() async {
        await _isar.basins.putAll(basins);
      });
    } catch (e) {
      debugPrint("Offline mode: Could not sync basins. Using cached data. $e");
    }
  }

  /// Fetch latest forecast for a specific basin and cache the advisory.
  /// Field names here must match the FastAPI response (see app/models/schemas.py).
  Future<void> syncForecast(String basinId, String role, String language) async {
    try {
      final data = await _apiClient.getForecast(basinId, role, language);

      final risk = data['risk'] as Map<String, dynamic>;
      final impact = data['impact'] as Map<String, dynamic>;
      final advisoryText = _formatAdvisory(data['advisory']);

      final healthFacilities =
          ((impact['clinics_at_risk'] ?? 0) as num).toInt() +
              ((impact['hospitals_at_risk'] ?? 0) as num).toInt();

      // Extract the 7-day discharge series for the chart.
      List<double> dischargeSeries = [];
      double floodThreshold = 0;
      final discharge = data['discharge'];
      if (discharge is Map<String, dynamic>) {
        floodThreshold = (discharge['flood_threshold'] as num?)?.toDouble() ?? 0;
        final dischargeData = discharge['data'] as List<dynamic>?;
        if (dischargeData != null) {
          // Take the last 7 entries (most recent days).
          final recent = dischargeData.length > 7
              ? dischargeData.sublist(dischargeData.length - 7)
              : dischargeData;
          dischargeSeries = recent
              .map((d) => ((d['discharge_mean'] ?? 0) as num).toDouble())
              .toList();
        }
      }

      await _isar.writeTxn(() async {
        var forecast =
            await _isar.forecasts.where().basinIdEqualTo(basinId).findFirst();

        forecast ??= Forecast()
          ..basinId = basinId
          ..advisoryKeys = []
          ..advisoryValues = [];

        forecast
          ..riskLevel = risk['risk_level'] ?? 'LOW'
          ..probability = (risk['probability'] as num).toDouble()
          ..thresholdExceedanceDays = risk['threshold_exceedance_days']
          ..peopleAtRisk =
              ((impact['estimated_population_at_risk'] ?? 0) as num).toInt()
          ..schoolsAtRisk = ((impact['schools_at_risk'] ?? 0) as num).toInt()
          ..clinicsAtRisk = healthFacilities
          ..dischargeSeries = dischargeSeries
          ..floodThreshold = floodThreshold
          ..lastSynced = DateTime.now();

        // Update cached advisory dictionary (keyed by "language_role")
        final cacheKey = "${language}_$role";
        final index = forecast.advisoryKeys.indexOf(cacheKey);

        if (index != -1) {
          forecast.advisoryValues[index] = advisoryText;
        } else {
          forecast.advisoryKeys = [...forecast.advisoryKeys, cacheKey];
          forecast.advisoryValues = [...forecast.advisoryValues, advisoryText];
        }

        await _isar.forecasts.put(forecast);
      });
    } catch (e) {
      debugPrint("Offline mode: Could not sync forecast. Using cached data. $e");
    }
  }

  /// The advisory arrives as an object; flatten it to readable text for caching.
  String _formatAdvisory(dynamic advisory) {
    if (advisory is! Map) return advisory?.toString() ?? '';
    final title = (advisory['title'] ?? '').toString().trim();
    final body = (advisory['body'] ?? '').toString().trim();
    final actions = (advisory['actions'] as List?)
            ?.map((a) => '• $a')
            .join('\n') ??
        '';
    return [title, body, actions]
        .where((s) => s.isNotEmpty)
        .join('\n\n');
  }

  /// Uploads queued community reports. A report is only marked synced once the
  /// backend accepts it, so failures stay in the queue and retry next time.
  Future<void> syncPendingReports() async {
    final pending =
        await _isar.communityReports.where().isSyncedEqualTo(false).findAll();

    var uploaded = 0;
    for (var report in pending) {
      try {
        await _apiClient.uploadReport(report);
        await _isar.writeTxn(() async {
          report.isSynced = true;
          await _isar.communityReports.put(report);
        });
        uploaded++;
      } catch (e) {
        debugPrint("Could not upload report ${report.id}; will retry. $e");
      }
    }
    debugPrint("Synced $uploaded of ${pending.length} pending report(s).");
  }
}
