import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'providers/prefs_provider.dart';
import 'services/auth_service.dart';
import 'ui/screens/dashboard_screen.dart';
import 'ui/theme.dart';

/// Public Supabase project — the same client URL + publishable key the web
/// dashboard ships. These are *public* (RLS on the server is what protects
/// data), so embedding them is safe and lets the released APK offer sign-in
/// without every build having to pass `--dart-define`. A `--dart-define`
/// override still wins, e.g. to point a debug build at a staging project.
const _defaultSupabaseUrl = 'https://gptfhrvzqmkyqymihycc.supabase.co';
const _defaultSupabaseKey = 'sb_publishable_9QmGTai_XeXdWA3lefWzng_zAHSB5Zg';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // The default virtual-display platform view renders a blank map under
  // Impeller on Vulkan-capable devices; hybrid composition draws correctly.
  MapLibreMap.useHybridComposition = true;

  // Load the owner's saved choices before the first frame so the UI opens
  // straight into their role, language, and home basin.
  final prefs = await SharedPreferences.getInstance();

  const overrideUrl = String.fromEnvironment('SUPABASE_URL');
  const overrideKey = String.fromEnvironment('SUPABASE_KEY');
  final supabaseUrl = overrideUrl.isNotEmpty ? overrideUrl : _defaultSupabaseUrl;
  final supabaseKey = overrideKey.isNotEmpty ? overrideKey : _defaultSupabaseKey;

  if (supabaseUrl.isNotEmpty && supabaseKey.isNotEmpty) {
    try {
      await Supabase.initialize(
        url: supabaseUrl,
        // Newer Supabase projects call this the "publishable" key (anon is the
        // deprecated alias). Both are the same public client key.
        publishableKey: supabaseKey,
      );
      // Sign-in is optional: if Supabase can't start (e.g. no network at
      // launch) the app still opens straight to the dashboard, just without
      // the account features.
      AuthService.initialized = true;
    } catch (e) {
      debugPrint('Supabase init failed — sign-in disabled this session: $e');
    }
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
