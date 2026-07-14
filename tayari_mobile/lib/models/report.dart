import 'package:isar/isar.dart';

part 'report.g.dart';

@collection
class CommunityReport {
  Id id = Isar.autoIncrement;

  late String basinId;
  late double latitude;
  late double longitude;
  late String status; // "Water rising", "Road flooded", "All clear"
  
  late String compressedPhotoPath; // Local path to the compressed image

  late DateTime createdAt;

  @Index()
  bool isSynced = false; // Queue flag for offline support
}
