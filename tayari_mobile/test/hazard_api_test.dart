import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:tayari_mobile/services/hazard_api.dart';

void main() {
  group('Place.label', () {
    test('drops the duplicated admin area geocoders produce', () {
      const p = Place(latitude: 27.7, longitude: 85.3, name: 'Kathmandu', admin1: 'Kathmandu', country: 'Nepal');
      expect(p.label, 'Kathmandu, Nepal');
    });

    test('falls back to coordinates when unnamed', () {
      const p = Place(latitude: -1.2864, longitude: 36.8172);
      expect(p.label, '-1.286, 36.817');
    });

    test('takes the server name without overwriting a chosen one', () {
      const unnamed = Place(latitude: 1, longitude: 2);
      expect(unnamed.withServerLocation({'name': 'Server'}).name, 'Server');
      const named = Place(latitude: 1, longitude: 2, name: 'Mine');
      expect(named.withServerLocation({'name': 'Server'}).name, 'Mine');
    });

    test('query omits null fields', () {
      const p = Place(latitude: 1, longitude: 2, name: 'X');
      expect(p.query, {'lat': 1.0, 'lon': 2.0, 'name': 'X'});
    });
  });

  test('HazardCache round-trips the last place and profile', () async {
    SharedPreferences.setMockInitialValues({});
    final cache = HazardCache(await SharedPreferences.getInstance());
    expect(cache.place, isNull);

    await cache.savePlace(const Place(latitude: 4.74, longitude: 45.2, name: 'Beledweyne'));
    await cache.saveProfile({'overall_risk': 'HIGH', 'hazards': []});

    expect(cache.place!.name, 'Beledweyne');
    expect(cache.profile!['overall_risk'], 'HIGH');
    expect(cache.savedAt, isNotNull);
  });
}
