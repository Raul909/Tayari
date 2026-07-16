import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'providers/prefs_provider.dart';
import 'ui/screens/dashboard_screen.dart';
import 'ui/theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Load the owner's saved choices before the first frame so the UI opens
  // straight into their role, language, and home basin.
  final prefs = await SharedPreferences.getInstance();

  runApp(
    ProviderScope(
      overrides: [sharedPrefsProvider.overrideWithValue(prefs)],
      child: const TayariApp(),
    ),
  );
}

class TayariApp extends StatelessWidget {
  const TayariApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Tayari',
      debugShowCheckedModeBanner: false,
      theme: buildTayariTheme(),
      home: const DashboardScreen(),
    );
  }
}
