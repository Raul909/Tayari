import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/user_prefs.dart';
import '../../providers/basin_provider.dart';
import '../../providers/prefs_provider.dart';
import '../theme.dart';

/// Where the owner sets their personal choices once. Everything the app shows —
/// alerts, stats, and advice — then defaults to these until they change them.
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final prefs = ref.watch(userPrefsProvider);
    final notifier = ref.read(userPrefsProvider.notifier);
    final basinsAsync = ref.watch(basinsStreamProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('My settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const _SectionLabel('Who advice is written for'),
          const SizedBox(height: 8),
          _Card(
            child: DropdownButtonFormField<String>(
              initialValue: prefs.role,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'My role'),
              items: [
                for (final r in kRoleOptions)
                  DropdownMenuItem(value: r.value, child: Text(r.label)),
              ],
              onChanged: (v) {
                if (v != null) notifier.setRole(v);
              },
            ),
          ),
          const SizedBox(height: 20),

          const _SectionLabel('Language for alerts & advice'),
          const SizedBox(height: 8),
          _Card(
            child: DropdownButtonFormField<String>(
              initialValue: prefs.language,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'My language'),
              items: [
                for (final l in kLanguageOptions)
                  DropdownMenuItem(value: l.value, child: Text(l.label)),
              ],
              onChanged: (v) {
                if (v != null) notifier.setLanguage(v);
              },
            ),
          ),
          const SizedBox(height: 20),

          const _SectionLabel('My home basin'),
          const SizedBox(height: 4),
          const Text(
            'Pinned to the top of the list so it is one tap away.',
            style: TextStyle(color: AppColors.textMuted, fontSize: 13),
          ),
          const SizedBox(height: 8),
          _Card(
            child: basinsAsync.when(
              data: (basins) {
                if (basins.isEmpty) {
                  return const Text(
                    'No basins synced yet. Connect to the internet, then set '
                    'your home basin here.',
                    style: TextStyle(color: AppColors.textMuted),
                  );
                }
                return DropdownButtonFormField<String>(
                  initialValue: basins.any((b) => b.basinId == prefs.homeBasinId)
                      ? prefs.homeBasinId
                      : null,
                  isExpanded: true,
                  decoration: const InputDecoration(labelText: 'Home basin'),
                  items: [
                    const DropdownMenuItem(value: null, child: Text('None')),
                    for (final b in basins)
                      DropdownMenuItem(
                        value: b.basinId,
                        child: Text('${b.name} · ${b.country}'),
                      ),
                  ],
                  onChanged: (v) => notifier.setHomeBasin(v),
                );
              },
              loading: () => const Padding(
                padding: EdgeInsets.symmetric(vertical: 8),
                child: LinearProgressIndicator(),
              ),
              error: (_, _) => const Text(
                'Could not load basins.',
                style: TextStyle(color: AppColors.riskHigh),
              ),
            ),
          ),
          const SizedBox(height: 28),

          Text(
            'Advisories will be written for a '
            '${UserPrefs.roleLabel(prefs.role).toLowerCase()} in '
            '${UserPrefs.languageLabel(prefs.language)}. '
            'These choices stay on this phone.',
            style: const TextStyle(color: AppColors.textSecondary, fontSize: 13, height: 1.5),
          ),
        ],
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  final String text;
  const _SectionLabel(this.text);

  @override
  Widget build(BuildContext context) => Text(
        text,
        style: const TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w600,
          color: AppColors.textPrimary,
        ),
      );
}

class _Card extends StatelessWidget {
  final Widget child;
  const _Card({required this.child});

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: AppColors.border),
        ),
        child: child,
      );
}
