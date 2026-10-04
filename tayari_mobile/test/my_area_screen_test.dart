import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:tayari_mobile/providers/prefs_provider.dart';
import 'package:tayari_mobile/services/hazard_api.dart';
import 'package:tayari_mobile/ui/screens/hazard_detail_screen.dart';
import 'package:tayari_mobile/ui/screens/my_area_screen.dart';

const _profile = {
  'overall_risk': 'HIGH',
  'headline': 'Volcanic activity leads at Manila',
  'partial': false,
  'languages': ['en'],
  'screened_out': ['tsunami'],
  'location': {'name': 'Manila', 'country': 'Philippines'},
  'hazards': [
    {
      'hazard': 'volcano',
      'risk_level': 'HIGH',
      'headline': 'Taal is erupting — 66 km away',
      'onset': 'hours',
      'susceptibility': 0.9,
      'indicators': [
        {'label': 'Distance', 'value': '66 km'},
      ],
      'events': [],
      'data_sources': ['Smithsonian GVP'],
    },
    {
      'hazard': 'flood',
      'risk_level': 'LOW',
      'headline': 'River levels are normal',
      'onset': 'days',
      'susceptibility': 0.2,
      'indicators': [],
      'events': [],
      'data_sources': [],
    },
  ],
};

class _FakeApi extends HazardApi {
  @override
  Future<Map<String, dynamic>> profile(Place place) async => Map<String, dynamic>.from(_profile);

  @override
  Future<Map<String, dynamic>> advisory(String hazard, Place place,
          {String role = 'general', String language = 'en'}) async =>
      {
        'advisory': {
          'title': 'Volcano — High at Manila',
          'body': 'Keep dust masks ready.',
          'actions': ['Stay out of river valleys'],
          'language': 'en',
          'requested_language': 'en',
          'ai_generated': false,
        },
      };

  @override
  Future<List<Place>> search(String query) async => [];
}

Future<void> _pump(WidgetTester tester, Map<String, Object> stored) async {
  SharedPreferences.setMockInitialValues(stored);
  final prefs = await SharedPreferences.getInstance();
  await tester.pumpWidget(ProviderScope(
    overrides: [
      sharedPrefsProvider.overrideWithValue(prefs),
      hazardApiProvider.overrideWithValue(_FakeApi()),
    ],
    child: const MaterialApp(home: MyAreaScreen()),
  ));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('first launch offers location, search and examples', (tester) async {
    await _pump(tester, {});
    expect(find.text('What threatens where you are?'), findsOneWidget);
    expect(find.text('Use my location'), findsOneWidget);
    expect(find.text('Nairobi'), findsOneWidget);
  });

  testWidgets('picking a place shows the answer and opens a hazard', (tester) async {
    await _pump(tester, {});
    await tester.tap(find.text('Manila'));
    await tester.pumpAndSettle();

    expect(find.text('Take action'), findsOneWidget);
    expect(find.text('Taal is erupting — 66 km away'), findsOneWidget);
    final list = find.descendant(of: find.byType(ListView), matching: find.byType(Scrollable)).first;
    await tester.scrollUntilVisible(find.textContaining('Not relevant here: Tsunami'), 200,
        scrollable: list);
    expect(find.textContaining('Not relevant here: Tsunami'), findsOneWidget);

    await tester.scrollUntilVisible(find.text('What to do about volcano →'), -200,
        scrollable: list);
    await tester.tap(find.text('What to do about volcano →'));
    await tester.pumpAndSettle();
    expect(find.byType(HazardDetailScreen), findsOneWidget);
    expect(find.text('Stay out of river valleys'), findsOneWidget);
  });
}
