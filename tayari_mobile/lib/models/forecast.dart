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
