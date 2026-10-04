import 'package:flutter/material.dart';

import 'screens/community_reports_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/my_area_screen.dart';
import 'screens/settings_screen.dart';

/// The four places the app goes, as a bottom navigation bar.
///
/// These used to be five unlabelled icons squeezed into the dashboard's app
/// bar — refresh, reports, feedback, settings, account — which on a small phone
/// meant guessing what each one did. Destinations now have names and sit under
/// the thumb; the app bar keeps only actions that belong to the current screen.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  // Built once and kept alive in an IndexedStack, so switching tabs does not
  // reload the map or lose a half-typed search.
  static const _screens = <Widget>[
    MyAreaScreen(),
    DashboardScreen(),
    CommunityReportsScreen(),
    SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _index, children: _screens),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.place_outlined),
            selectedIcon: Icon(Icons.place),
            label: 'My area',
          ),
          NavigationDestination(
            icon: Icon(Icons.water_outlined),
            selectedIcon: Icon(Icons.water),
            label: 'Basins',
          ),
          NavigationDestination(
            icon: Icon(Icons.forum_outlined),
            selectedIcon: Icon(Icons.forum),
            label: 'Reports',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: 'Settings',
          ),
        ],
      ),
    );
  }
}
