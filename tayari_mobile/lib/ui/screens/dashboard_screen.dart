import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import '../../providers/basin_provider.dart';
import 'basin_detail_screen.dart';

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  MapLibreMapController? mapController;

  void _onMapCreated(MapLibreMapController controller) {
    mapController = controller;
  }

  @override
  Widget build(BuildContext context) {
    // Listen to the live Isar database stream for basins
    final basinsAsyncValue = ref.watch(basinsStreamProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('🌊 Tayari', style: TextStyle(fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            icon: const Icon(Icons.sync),
            onPressed: () {
              // The stream provider auto-syncs on watch, but we could expose a manual sync here
            },
          ),
        ],
      ),
      body: Stack(
        children: [
          // Offline-capable MapLibre Map
          MapLibreMap(
            onMapCreated: _onMapCreated,
            initialCameraPosition: const CameraPosition(
              target: LatLng(5.1521, 46.1996), // Horn of Africa center
              zoom: 5.0,
            ),
            styleString: 'https://tiles.openfreemap.org/styles/positron', // In production, we'd load local .mbtiles
          ),

          // Floating UI for Basin list
          Positioned(
            left: 16,
            right: 16,
            bottom: 16,
            child: Container(
              height: 200,
              decoration: BoxDecoration(
                color: const Color(0xFF112240).withOpacity(0.9),
                borderRadius: BorderRadius.circular(16),
              ),
              child: basinsAsyncValue.when(
                data: (basins) {
                  if (basins.isEmpty) {
                    return const Center(child: Text("No data yet. Syncing..."));
                  }
                  return ListView.builder(
                    itemCount: basins.length,
                    itemBuilder: (context, index) {
                      final basin = basins[index];
                      return ListTile(
                        title: Text(basin.name, style: const TextStyle(fontWeight: FontWeight.bold)),
                        subtitle: Text('${basin.country} • ${basin.currentRisk} Risk'),
                        trailing: Text(
                          basin.floodProbability != null 
                            ? '${(basin.floodProbability! * 100).toStringAsFixed(0)}%' 
                            : '—',
                          style: TextStyle(
                            color: basin.currentRisk == 'HIGH' ? Colors.red : Colors.green,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        onTap: () {
                          // Fly to basin on map
                          mapController?.animateCamera(
                            CameraUpdate.newLatLngZoom(
                              LatLng(basin.latitude, basin.longitude),
                              9.0,
                            ),
                          );
                          
                          // Push to Detail Screen
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
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (e, st) => Center(child: Text('Offline Mode Error: $e')),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
