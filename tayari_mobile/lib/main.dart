import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'providers/prefs_provider.dart';
import 'ui/screens/dashboard_screen.dart';
import 'ui/theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // The default virtual-display platform view renders a blank map under
  // Impeller on Vulkan-capable devices; hybrid composition draws correctly.
  MapLibreMap.useHybridComposition = true;

  // Load the owner's saved choices before the first frame so the UI opens
  // straight into their role, language, and home basin.
  final prefs = await SharedPreferences.getInstance();

  const supabaseUrl = String.fromEnvironment('SUPABASE_URL');
  const supabaseKey = String.fromEnvironment('SUPABASE_KEY');

  if (supabaseUrl.isNotEmpty && supabaseKey.isNotEmpty) {
    await Supabase.initialize(
      url: supabaseUrl,
      anonKey: supabaseKey,
    );
  }

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
