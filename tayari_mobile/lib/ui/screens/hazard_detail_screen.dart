import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/user_prefs.dart';
import '../../providers/prefs_provider.dart';
import '../../services/hazard_api.dart';
import '../hazard_meta.dart';
import '../theme.dart';
import 'my_area_screen.dart';

/// One hazard at one place: what to do first, then what it is based on.
///
/// The advisory leads because it is the reason someone opened this. The
/// measurements that justify it follow, for anyone who wants to check.
class HazardDetailScreen extends ConsumerStatefulWidget {
  final Map<String, dynamic> risk;
  final Place place;
  final List<String> languages;

  const HazardDetailScreen({
    super.key,
    required this.risk,
    required this.place,
    required this.languages,
  });

  @override
  ConsumerState<HazardDetailScreen> createState() => _HazardDetailScreenState();
}

class _HazardDetailScreenState extends ConsumerState<HazardDetailScreen> {
  late String _role;
  late String _language;
  Map<String, dynamic>? _advisory;
  bool _loading = true;
  String? _error;
  int _requestId = 0;

  @override
  void initState() {
    super.initState();
    final prefs = ref.read(userPrefsProvider);
    _role = prefs.role;
    // Only languages actually spoken here; otherwise English, rather than a
    // saved Somali preference producing nothing useful in Peru.
    _language = widget.languages.contains(prefs.language) ? prefs.language : 'en';
    _fetch();
  }

  Future<void> _fetch() async {
    final id = ++_requestId;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await ref.read(hazardApiProvider).advisory(
            widget.risk['hazard'] as String,
            widget.place,
            role: _role,
            language: _language,
          );
      if (!mounted || id != _requestId) return;
      setState(() => _advisory = Map<String, dynamic>.from(data['advisory'] as Map));
    } catch (e) {
      if (!mounted || id != _requestId) return;
      setState(() => _error = 'The advice could not be loaded. The readings below are still current.');
    } finally {
      if (mounted && id == _requestId) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final risk = widget.risk;
    final meta = hazardMeta(risk['hazard'] as String);
    final level = risk['risk_level'] as String? ?? 'LOW';
    final indicators = List<Map>.from(risk['indicators'] as List? ?? const []);
    final events = List<Map>.from(risk['events'] as List? ?? const []);
    final sources = List<String>.from(risk['data_sources'] as List? ?? const []);

    return Scaffold(
      appBar: AppBar(title: Text(meta.label)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          Row(
            children: [
              Text(meta.icon, style: const TextStyle(fontSize: 30)),
              const SizedBox(width: 12),
              RiskBadge(level: level),
              const SizedBox(width: 8),
              Text(kOnsetLabels[risk['onset']] ?? '',
                  style: const TextStyle(color: AppColors.textSecondary)),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            risk['headline'] as String? ?? '',
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600, height: 1.35),
          ),
          if (risk['summary'] != null) ...[
            const SizedBox(height: 6),
            Text(risk['summary'] as String,
                style: const TextStyle(color: AppColors.textSecondary, height: 1.5)),
          ],
          if (risk['lead_time'] != null) ...[
            const SizedBox(height: 8),
            Text('Warning time: ${risk['lead_time']}',
                style: const TextStyle(fontSize: 13, color: AppColors.textMuted)),
          ],
          const SizedBox(height: 20),
          _sectionTitle('What to do'),
          _buildControls(),
          const SizedBox(height: 10),
          _buildAdvisory(level),
          if (indicators.isNotEmpty) ...[
            const SizedBox(height: 24),
            _sectionTitle('What this is based on'),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    for (final ind in indicators) ...[
                      Text((ind['label'] as String).toUpperCase(),
                          style: const TextStyle(
                              fontSize: 11, letterSpacing: 0.4, color: AppColors.textMuted)),
                      Text('${ind['value']}',
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                      if (ind['detail'] != null)
                        Text(ind['detail'] as String,
                            style: const TextStyle(fontSize: 12.5, color: AppColors.textSecondary)),
                      const SizedBox(height: 10),
                    ],
                  ],
                ),
              ),
            ),
          ],
          if (events.isNotEmpty) ...[
            const SizedBox(height: 16),
            _sectionTitle('Recent events'),
            Card(
              child: Column(
                children: [
                  for (final e in events)
                    ListTile(
                      title: Text(e['title'] as String? ?? ''),
                      subtitle: Text([
                        if (e['distance_km'] != null) '${(e['distance_km'] as num).round()} km away',
                        if (e['occurred_at'] != null)
                          DateTime.parse(e['occurred_at'] as String).toLocal().toString().substring(0, 16),
                      ].join(' · ')),
                    ),
                ],
              ),
            ),
          ],
          if (sources.isNotEmpty) ...[
            const SizedBox(height: 16),
            _sectionTitle('Where this comes from'),
            for (final s in sources)
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Text('• $s', style: const TextStyle(fontSize: 13, color: AppColors.textSecondary)),
              ),
          ],
        ],
      ),
    );
  }

  Widget _sectionTitle(String text) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Text(text, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
      );

  Widget _buildControls() {
    final langs = widget.languages;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        DropdownButtonFormField<String>(
          initialValue: _role,
          isExpanded: true,
          decoration: const InputDecoration(labelText: 'Written for'),
          items: [
            for (final r in kRoleOptions) DropdownMenuItem(value: r.value, child: Text(r.label)),
          ],
          onChanged: (v) {
            if (v == null || v == _role) return;
            setState(() => _role = v);
            _fetch();
          },
        ),
        if (langs.length > 1) ...[
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: [
              for (final code in langs)
                ChoiceChip(
                  label: Text(_languageLabel(code)),
                  selected: _language == code,
                  onSelected: (_) {
                    if (_language == code) return;
                    setState(() => _language = code);
                    _fetch();
                  },
                ),
            ],
          ),
        ],
      ],
    );
  }

  Widget _buildAdvisory(String level) {
    final advisory = _advisory;
    if (_loading && advisory == null) {
      return const Padding(
        padding: EdgeInsets.all(24),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (_error != null && advisory == null) {
      return Row(
        children: [
          Expanded(child: Text(_error!, style: const TextStyle(color: AppColors.riskHigh))),
          TextButton(onPressed: _fetch, child: const Text('Retry')),
        ],
      );
    }
    if (advisory == null) return const SizedBox.shrink();

    final color = AppColors.risk(level);
    final actions = List<String>.from(advisory['actions'] as List? ?? const []);
    final rtl = advisory['language'] == 'ar';
    return Opacity(
      opacity: _loading ? 0.5 : 1,
      child: Directionality(
        textDirection: rtl ? TextDirection.rtl : TextDirection.ltr,
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(10),
            border: Border(left: BorderSide(color: color, width: 4)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(advisory['title'] as String? ?? '',
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
              Text(advisory['body'] as String? ?? '', style: const TextStyle(height: 1.5)),
              for (final a in actions)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Padding(
                        padding: EdgeInsets.only(top: 2),
                        child: Icon(Icons.check_circle_outline, size: 18, color: AppColors.accent),
                      ),
                      const SizedBox(width: 8),
                      Expanded(child: Text(a, style: const TextStyle(height: 1.4))),
                    ],
                  ),
                ),
              if (advisory['language'] != advisory['requested_language']) ...[
                const SizedBox(height: 10),
                Text(
                  'Could not be written reliably in ${_languageLabel(advisory['requested_language'] as String? ?? '')}, '
                  'so it is shown in ${_languageLabel(advisory['language'] as String? ?? 'en')}.',
                  style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                ),
              ],
              const SizedBox(height: 10),
              Text(
                advisory['ai_generated'] == true
                    ? 'Written by AI from the readings below. AI can make mistakes — the readings and official sources are the record.'
                    : 'Standard safety guidance written by people.',
                style: const TextStyle(fontSize: 11.5, color: AppColors.textMuted),
              ),
            ],
          ),
        ),
      ),
    );
  }

  static String _languageLabel(String code) =>
      kLanguageOptions.where((l) => l.value == code).map((l) => l.label).firstOrNull ?? code;
}
