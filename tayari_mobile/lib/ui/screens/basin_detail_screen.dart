import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../models/basin.dart';
import '../../providers/basin_provider.dart';
import 'report_screen.dart';

class BasinDetailScreen extends ConsumerStatefulWidget {
  final Basin basin;
  const BasinDetailScreen({super.key, required this.basin});

  @override
  ConsumerState<BasinDetailScreen> createState() => _BasinDetailScreenState();
}

class _BasinDetailScreenState extends ConsumerState<BasinDetailScreen> {
  String selectedLanguage = 'en';
  String selectedRole = 'farmer';

  @override
  Widget build(BuildContext context) {
    final forecastAsync = ref.watch(forecastStreamProvider(widget.basin.basinId));

    return Scaffold(
      appBar: AppBar(
        title: Text('${widget.basin.name} Basin'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add_a_photo),
            tooltip: 'Report Flood',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => ReportScreen(basinId: widget.basin.basinId),
                ),
              );
            },
          )
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: forecastAsync.when(
          data: (forecast) {
            if (forecast == null) {
              return const Center(child: Text("Loading forecast data..."));
            }

            final advisory = forecast.getAdvisory(selectedLanguage, selectedRole);

            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Risk Header
                _buildRiskCard(forecast.riskLevel, forecast.probability),
                const SizedBox(height: 24),
                
                // Discharge Chart
                const Text("Forecasted River Discharge", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                const SizedBox(height: 16),
                _buildChart(),
                const SizedBox(height: 24),

                // Impact Stats
                const Text("Impact Assessment", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                const SizedBox(height: 16),
                _buildImpactRow(forecast.peopleAtRisk, forecast.schoolsAtRisk, forecast.clinicsAtRisk),
                const SizedBox(height: 24),

                // AI Advisory Engine
                const Text("AI Advisory", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: DropdownButton<String>(
                        value: selectedRole,
                        isExpanded: true,
                        items: const [
                          DropdownMenuItem(value: 'farmer', child: Text("For Farmers")),
                          DropdownMenuItem(value: 'officer', child: Text("For County Officers")),
                        ],
                        onChanged: (val) => setState(() => selectedRole = val!),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: DropdownButton<String>(
                        value: selectedLanguage,
                        isExpanded: true,
                        items: const [
                          DropdownMenuItem(value: 'en', child: Text("English")),
                          DropdownMenuItem(value: 'sw', child: Text("Swahili")),
                          DropdownMenuItem(value: 'so', child: Text("Somali")),
                        ],
                        onChanged: (val) => setState(() => selectedLanguage = val!),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.blueGrey.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    advisory ?? "Advisory fetching or not available offline for this language/role combination yet.",
                    style: const TextStyle(fontSize: 16, height: 1.5),
                  ),
                ),
                const SizedBox(height: 40),
              ],
            );
          },
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, st) => Center(child: Text("Error: $e")),
        ),
      ),
    );
  }

  Widget _buildRiskCard(String risk, double prob) {
    Color riskColor = Colors.green;
    if (risk == 'HIGH' || risk == 'EXTREME') riskColor = Colors.red;
    if (risk == 'MODERATE') riskColor = Colors.orange;

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: riskColor.withOpacity(0.2),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: riskColor, width: 2),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(risk.toUpperCase(), style: TextStyle(color: riskColor, fontSize: 24, fontWeight: FontWeight.bold)),
              const Text("Flood Risk Level"),
            ],
          ),
          Text("${(prob * 100).toStringAsFixed(0)}%", style: TextStyle(color: riskColor, fontSize: 32, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  Widget _buildChart() {
    return SizedBox(
      height: 200,
      child: LineChart(
        LineChartData(
          gridData: FlGridData(show: false),
          titlesData: FlTitlesData(show: false),
          borderData: FlBorderData(show: false),
          lineBarsData: [
            LineChartBarData(
              spots: const [
                FlSpot(0, 1),
                FlSpot(1, 1.5),
                FlSpot(2, 1.4),
                FlSpot(3, 3.4), // Spike
                FlSpot(4, 2),
                FlSpot(5, 2.2),
                FlSpot(6, 1.8),
              ],
              isCurved: true,
              color: Colors.blue,
              barWidth: 4,
              isStrokeCapRound: true,
              dotData: FlDotData(show: false),
              belowBarData: BarAreaData(show: true, color: Colors.blue.withOpacity(0.3)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildImpactRow(int people, int schools, int clinics) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        _impactBox(Icons.people, "People", people.toString()),
        _impactBox(Icons.school, "Schools", schools.toString()),
        _impactBox(Icons.local_hospital, "Clinics", clinics.toString()),
      ],
    );
  }

  Widget _impactBox(IconData icon, String label, String value) {
    return Column(
      children: [
        Icon(icon, size: 32, color: Colors.blueGrey),
        const SizedBox(height: 8),
        Text(value, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
        Text(label, style: const TextStyle(color: Colors.grey)),
      ],
    );
  }
}
