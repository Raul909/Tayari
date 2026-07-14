import 'package:isar/isar.dart';

part 'basin.g.dart';

@collection
class Basin {
  Id id = Isar.autoIncrement;

  @Index(unique: true, replace: true)
  late String basinId;

  late String name;
  late String river;
  late String country;

  late double latitude;
  late double longitude;

  late double currentDischarge;
  late String currentRisk; // LOW, MODERATE, HIGH, EXTREME
  
  double? floodProbability;
}
