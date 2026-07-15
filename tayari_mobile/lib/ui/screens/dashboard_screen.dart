import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import '../../providers/basin_provider.dart';
import '../../providers/db_provider.dart';
import '../theme.dart';
import 'basin_detail_screen.dart';

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  MapLibreMapController? mapController;
  bool _syncing = false;

  void _onMapCreated(MapLibreMapController controller) {
    mapController = controller;
  }

  Future<void> _manualSync() async {
    setState(() => _syncing = true);
    try {
      final service = await ref.read(syncServiceProvider.future);
      await service.syncBasins();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Basins up to date.')),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not reach the server. Showing cached data.')),
        );
      }
    } finally {
      if (mounted) setState(() => _syncing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final basinsAsyncValue = ref.watch(basinsStreamProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Tayari'),
        actions: [
          IconButton(
            icon: _syncing
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.refresh),
            tooltip: 'Refresh',
            onPressed: _syncing ? null : _manualSync,
          ),
        ],
      ),
      body: Stack(
        children: [
          MapLibreMap(
            onMapCreated: _onMapCreated,
            initialCameraPosition: const CameraPosition(
              target: LatLng(2.0, 42.0), // IGAD region
              zoom: 5.0,
            ),
            styleString: 'https://tiles.openfreemap.org/styles/positron',
          ),

          // Floating basin list
          Positioned(
            left: 12,
            right: 12,
            bottom: 12,
            child: Container(
              constraints: const BoxConstraints(maxHeight: 260),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.border),
                boxShadow: const [
                  BoxShadow(color: Color(0x14000000), blurRadius: 12, offset: Offset(0, 4)),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Padding(
                    padding: EdgeInsets.fromLTRB(16, 14, 16, 8),
                    child: Text(
                      'Monitored basins',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.4,
                        color: AppColors.textMuted,
                      ),
                    ),
                  ),
                  Flexible(
                    child: basinsAsyncValue.when(
                      data: (basins) {
                        if (basins.isEmpty) {
                          return const Padding(
                            padding: EdgeInsets.all(24),
                            child: Center(
                              child: Text(
                                'No data yet — syncing…',
                                style: TextStyle(color: AppColors.textMuted),
                              ),
                            ),
                          );
                        }
                        return ListView.separated(
                          shrinkWrap: true,
                          padding: const EdgeInsets.only(bottom: 8),
                          itemCount: basins.length,
                          separatorBuilder: (_, _) =>
                              const Divider(height: 1, color: AppColors.border),
                          itemBuilder: (context, index) {
                            final basin = basins[index];
                            return _BasinTile(
                              name: basin.name,
                              country: basin.country,
                              risk: basin.currentRisk,
                              probability: basin.floodProbability,
                              onTap: () {
                                mapController?.animateCamera(
                                  CameraUpdate.newLatLngZoom(
                                    LatLng(basin.latitude, basin.longitude),
                                    9.0,
                                  ),
                                );
                                Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                    builder: (_) => BasinDetailScreen(basin: basin),
                                  ),
                                );
                              },
                            );
                          },
                        );
                      },
                      loading: () => const Padding(
                        padding: EdgeInsets.all(24),
                        child: Center(child: CircularProgressIndicator()),
                      ),
                      error: (e, st) => const Padding(
                        padding: EdgeInsets.all(20),
                        child: Text(
                          'Could not load basins. Pull to refresh when back online.',
                          style: TextStyle(color: AppColors.riskHigh),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _BasinTile extends StatelessWidget {
  final String name;
  final String country;
  final String risk;
  final double? probability;
  final VoidCallback onTap;

  const _BasinTile({
    required this.name,
    required this.country,
    required this.risk,
    required this.probability,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final color = AppColors.risk(risk);
    final pct = probability != null
        ? '${(probability! * 100).toStringAsFixed(0)}%'
        : '—';

    return ListTile(
      dense: false,
      leading: Container(
        width: 40,
        height: 40,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          shape: BoxShape.circle,
          border: Border.all(color: color, width: 1.5),
        ),
        child: Text(
          pct,
          style: TextStyle(
            color: color,
            fontWeight: FontWeight.w600,
            fontSize: 12,
          ),
        ),
      ),
      title: Text(name, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15)),
      subtitle: Text(
        '$country · ${_titleCase(risk)} risk',
        style: const TextStyle(color: AppColors.textMuted, fontSize: 13),
      ),
      trailing: const Icon(Icons.chevron_right, color: AppColors.textMuted),
      onTap: onTap,
    );
  }

  String _titleCase(String s) =>
      s.isEmpty ? s : s[0].toUpperCase() + s.substring(1).toLowerCase();
}
