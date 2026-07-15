import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'ui/screens/dashboard_screen.dart';
import 'ui/theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    const ProviderScope(
      child: TayariApp(),
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
