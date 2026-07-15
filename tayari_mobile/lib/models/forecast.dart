import 'package:isar/isar.dart';

part 'forecast.g.dart';

@collection
class Forecast {
  Id id = Isar.autoIncrement;

  @Index(unique: true, replace: true)
  late String basinId;

  late String riskLevel;
  late double probability;
  int? thresholdExceedanceDays;

  // Impact Assessment
  late int peopleAtRisk;
  late int schoolsAtRisk;
  late int clinicsAtRisk;

  // 7-day discharge series (discharge_mean values, chronological order).
  // Cached from the backend DischargeTimeSeries so the chart shows real data.
  List<double> dischargeSeries = [];

  // Flood threshold in m³/s — drawn as a reference line on the chart.
  double floodThreshold = 0;

  // Advisory cache (per language and role)
  // Format: "en_farmer": "advisory text..."
  late List<String> advisoryKeys;
  late List<String> advisoryValues;

  DateTime lastSynced = DateTime.now();

  String? getAdvisory(String language, String role) {
    final key = "${language}_$role";
    final index = advisoryKeys.indexOf(key);
    if (index != -1) {
      return advisoryValues[index];
    }
    return null;
  }
}
