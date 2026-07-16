import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../models/basin.dart';
import '../../models/forecast.dart';
import '../../models/user_prefs.dart';
import '../../providers/basin_provider.dart';
import '../../providers/db_provider.dart';
import '../../providers/prefs_provider.dart';
import '../theme.dart';
import 'report_screen.dart';

class BasinDetailScreen extends ConsumerStatefulWidget {
  final Basin basin;
  const BasinDetailScreen({super.key, required this.basin});

  @override
  ConsumerState<BasinDetailScreen> createState() => _BasinDetailScreenState();
}

class _BasinDetailScreenState extends ConsumerState<BasinDetailScreen> {
  late String selectedLanguage;
  late String selectedRole;
  bool _syncing = false;

  @override
  void initState() {
    super.initState();
    // Open straight into the owner's saved audience + language so the advisory
    // is already tailored to them without any extra taps.
    final prefs = ref.read(userPrefsProvider);
    selectedRole = prefs.role;
    selectedLanguage = prefs.language;
    // Kick off a forecast fetch as soon as the screen opens. Without this the
    // forecast/advisory would never be requested and the screen would hang on
    // "loading" forever.
    WidgetsBinding.instance.addPostFrameCallback((_) => _syncForecast());
  }

  Future<void> _syncForecast() async {
    setState(() => _syncing = true);
    try {
      final service = await ref.read(syncServiceProvider.future);
      await service.syncForecast(
        widget.basin.basinId,
        selectedRole,
        selectedLanguage,
      );
    } finally {
      if (mounted) setState(() => _syncing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final forecastAsync = ref.watch(forecastStreamProvider(widget.basin.basinId));

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.basin.name),
        actions: [
          IconButton(
            icon: const Icon(Icons.add_a_photo_outlined),
            tooltip: 'Report from the field',
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
      body: forecastAsync.when(
        data: (forecast) {
          if (forecast == null) {
            return _CenteredMessage(
              icon: _syncing ? null : Icons.cloud_off_outlined,
              text: _syncing
                  ? 'Loading forecast…'
                  : 'No forecast cached yet.\nConnect to the internet and refresh.',
              showSpinner: _syncing,
            );
          }

          final advisory = forecast.getAdvisory(selectedLanguage, selectedRole);

          return SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildRiskCard(
                  forecast.riskLevel,
                  forecast.probability,
                  forecast.thresholdExceedanceDays,
                ),
                const SizedBox(height: 24),

                _sectionTitle('River discharge (7-day trend)'),
                const SizedBox(height: 12),
                _card(child: SizedBox(height: 180, child: _buildChart(forecast))),
                const SizedBox(height: 24),

                _sectionTitle('Impact assessment'),
                const SizedBox(height: 12),
                _buildImpactRow(
                  forecast.peopleAtRisk,
                  forecast.schoolsAtRisk,
                  forecast.clinicsAtRisk,
                ),
                const SizedBox(height: 24),

                _sectionTitle('Advisory'),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(child: _dropdownRole()),
                    const SizedBox(width: 12),
                    Expanded(child: _dropdownLanguage()),
                  ],
                ),
                const SizedBox(height: 12),
                _card(
                  background: AppColors.risk(forecast.riskLevel)
                      .withValues(alpha: 0.08),
                  borderColor: AppColors.risk(forecast.riskLevel)
                      .withValues(alpha: 0.4),
                  child: Text(
                    advisory ??
                        (_syncing
                            ? 'Fetching the advisory…'
                            : 'This advisory is not cached offline for the selected '
                                'language and audience yet. Connect and it will download.'),
                    style: const TextStyle(fontSize: 15, height: 1.55),
                  ),
                ),
                const SizedBox(height: 40),
              ],
            ),
          );
        },
        loading: () => const _CenteredMessage(text: 'Loading…', showSpinner: true),
        error: (e, st) => const _CenteredMessage(
          icon: Icons.error_outline,
          text: 'Something went wrong loading this basin.',
        ),
      ),
    );
  }

  // ── Widgets ──────────────────────────────────────────────────────────────

  Widget _sectionTitle(String text) => Text(
        text,
        style: const TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w600,
          color: AppColors.textPrimary,
        ),
      );

  Widget _card({required Widget child, Color? background, Color? borderColor}) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: background ?? AppColors.surface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: borderColor ?? AppColors.border),
      ),
      child: child,
    );
  }

  Widget _dropdownRole() {
    return DropdownButtonFormField<String>(
      initialValue: selectedRole,
      isExpanded: true,
      decoration: const InputDecoration(
        labelText: 'Audience',
        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      ),
      items: [
        for (final r in kRoleOptions)
          DropdownMenuItem(value: r.value, child: Text(r.label)),
      ],
      onChanged: (val) {
        if (val == null) return;
        setState(() => selectedRole = val);
        // Remember this as the owner's choice for next time.
        ref.read(userPrefsProvider.notifier).setRole(val);
        _syncForecast();
      },
    );
  }

  Widget _dropdownLanguage() {
    return DropdownButtonFormField<String>(
      initialValue: selectedLanguage,
      isExpanded: true,
      decoration: const InputDecoration(
        labelText: 'Language',
        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      ),
      items: [
        for (final l in kLanguageOptions)
          DropdownMenuItem(value: l.value, child: Text(l.label)),
      ],
      onChanged: (val) {
        if (val == null) return;
        setState(() => selectedLanguage = val);
        // Remember this as the owner's choice for next time.
        ref.read(userPrefsProvider.notifier).setLanguage(val);
        _syncForecast();
      },
    );
  }

  Widget _buildRiskCard(String risk, double prob, int? thresholdDays) {
    final riskColor = AppColors.risk(risk);
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: riskColor.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: riskColor.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    risk.toUpperCase(),
                    style: TextStyle(
                      color: riskColor,
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const Text(
                    'Flood risk level',
                    style: TextStyle(color: AppColors.textSecondary),
                  ),
                ],
              ),
              Text(
                '${(prob * 100).toStringAsFixed(0)}%',
                style: TextStyle(
                  color: riskColor,
                  fontFamily: AppFonts.mono,
                  fontSize: 30,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            thresholdDays != null
                ? 'Flood threshold may be crossed in $thresholdDays '
                    'day${thresholdDays == 1 ? '' : 's'}.'
                : 'No threshold exceedance expected in the next 7 days.',
            style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
          ),
        ],
      ),
    );
  }

  // Real 7-day discharge trend from cached data.
  Widget _buildChart(Forecast forecast) {
    final series = forecast.dischargeSeries;
    if (series.isEmpty) {
      return const Center(
        child: Text(
          'No discharge data cached yet.\nConnect to the internet to load.',
          textAlign: TextAlign.center,
          style: TextStyle(color: AppColors.textMuted, fontSize: 13),
        ),
      );
    }

    final spots = <FlSpot>[
      for (var i = 0; i < series.length; i++) FlSpot(i.toDouble(), series[i]),
    ];

    final threshold = forecast.floodThreshold;
    final maxY = spots.map((s) => s.y).reduce((a, b) => a > b ? a : b);
    final chartMax = (maxY > threshold ? maxY : threshold) * 1.15;

    return LineChart(
      LineChartData(
        minY: 0,
        maxY: chartMax,
        gridData: const FlGridData(show: false),
        titlesData: const FlTitlesData(show: false),
        borderData: FlBorderData(show: false),
        extraLinesData: ExtraLinesData(
          horizontalLines: [
            if (threshold > 0)
              HorizontalLine(
                y: threshold,
                color: AppColors.riskHigh.withValues(alpha: 0.5),
                strokeWidth: 1.5,
                dashArray: [6, 4],
                label: HorizontalLineLabel(
                  show: true,
                  alignment: Alignment.topRight,
                  style: const TextStyle(
                    color: AppColors.riskHigh,
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                  ),
                  labelResolver: (_) => 'Flood threshold',
                ),
              ),
          ],
        ),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: AppColors.accent,
            barWidth: 3,
            isStrokeCapRound: true,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              color: AppColors.accent.withValues(alpha: 0.12),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildImpactRow(int people, int schools, int health) {
    return Row(
      children: [
        Expanded(child: _impactBox(Icons.people_outline, 'People', _compact(people))),
        const SizedBox(width: 10),
        Expanded(child: _impactBox(Icons.school_outlined, 'Schools', schools.toString())),
        const SizedBox(width: 10),
        Expanded(
          child: _impactBox(
            Icons.local_hospital_outlined,
            'Health',
            health.toString(),
          ),
        ),
      ],
    );
  }

  Widget _impactBox(IconData icon, String label, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 16),
      decoration: BoxDecoration(
        color: AppColors.surfaceSunken,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        children: [
          Icon(icon, size: 26, color: AppColors.textSecondary),
          const SizedBox(height: 8),
          Text(value,
              style: const TextStyle(
                fontFamily: AppFonts.mono,
                fontSize: 18,
                fontWeight: FontWeight.w700,
              )),
          Text(label, style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
        ],
      ),
    );
  }

  String _compact(int n) {
    if (n >= 1000000) return '${(n / 1000000).toStringAsFixed(1)}M';
    if (n >= 1000) return '${(n / 1000).toStringAsFixed(1)}k';
    return n.toString();
  }
}

class _CenteredMessage extends StatelessWidget {
  final IconData? icon;
  final String text;
  final bool showSpinner;

  const _CenteredMessage({
    this.icon,
    required this.text,
    this.showSpinner = false,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (showSpinner) const CircularProgressIndicator(),
            if (icon != null && !showSpinner)
              Icon(icon, size: 40, color: AppColors.textMuted),
            const SizedBox(height: 16),
            Text(
              text,
              textAlign: TextAlign.center,
              style: const TextStyle(color: AppColors.textSecondary),
            ),
          ],
        ),
      ),
    );
  }
}
