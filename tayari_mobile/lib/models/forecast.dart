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

  // The language the backend actually delivered for each cache key, parallel to
  // advisoryKeys. The backend can fall back to a regional language or English
  // when it can't write the requested one (e.g. Daasanach) — this lets the app
  // tell the reader why the advisory isn't in their language. Empty string means
  // "unknown" (e.g. an entry cached before this field existed).
  List<String> advisoryLangValues = [];

  DateTime lastSynced = DateTime.now();

  String? getAdvisory(String language, String role) {
    final key = "${language}_$role";
    final index = advisoryKeys.indexOf(key);
    if (index != -1) {
      return advisoryValues[index];
    }
    return null;
  }

  /// The language actually delivered for this language/role advisory, or null
  /// if unknown. Compare against the requested language to detect a fallback.
  String? getAdvisoryLanguage(String language, String role) {
    final key = "${language}_$role";
    final index = advisoryKeys.indexOf(key);
    if (index != -1 && index < advisoryLangValues.length) {
      final lang = advisoryLangValues[index];
      return lang.isEmpty ? null : lang;
    }
    return null;
  }
}
