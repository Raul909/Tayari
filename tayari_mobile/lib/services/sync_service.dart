import 'package:isar/isar.dart';
import '../models/basin.dart';
import '../models/forecast.dart';
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
          ..latitude = json['latitude']
          ..longitude = json['longitude']
          ..currentDischarge = (json['current_discharge'] ?? 0).toDouble()
          ..currentRisk = json['current_risk']
          ..floodProbability = json['flood_probability']?.toDouble();
      }).toList();

      await _isar.writeTxn(() async {
        await _isar.basins.putAll(basins);
      });
    } catch (e) {
      print("Offline mode: Could not sync basins. Using cached data. $e");
    }
  }

  /// Fetch latest forecast for a specific basin and cache the advisory
  Future<void> syncForecast(String basinId, String role, String language) async {
    try {
      final data = await _apiClient.getForecast(basinId, role, language);
      
      final risk = data['risk'];
      final impact = data['impact'];
      final advisoryText = data['advisory'];

      await _isar.writeTxn(() async {
        // Try to find existing forecast cache
        var forecast = await _isar.forecasts.where().basinIdEqualTo(basinId).findFirst();
        
        if (forecast == null) {
          forecast = Forecast()
            ..basinId = basinId
            ..advisoryKeys = []
            ..advisoryValues = [];
        }

        forecast
          ..riskLevel = risk['risk_level']
          ..probability = risk['probability'].toDouble()
          ..thresholdExceedanceDays = risk['threshold_exceedance_days']
          ..peopleAtRisk = impact['population_at_risk'] ?? 0
          ..schoolsAtRisk = impact['infrastructure_at_risk']['schools'] ?? 0
          ..clinicsAtRisk = impact['infrastructure_at_risk']['clinics'] ?? 0
          ..lastSynced = DateTime.now();

        // Update cached advisory dictionary
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
      print("Offline mode: Could not sync forecast. Using cached data. $e");
    }
  }
}
