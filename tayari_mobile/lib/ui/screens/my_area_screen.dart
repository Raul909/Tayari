import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';

import '../../providers/prefs_provider.dart';
import '../../services/hazard_api.dart';
import '../hazard_meta.dart';
import '../theme.dart';
import '../widgets/account_action.dart';
import 'hazard_detail_screen.dart';

final hazardApiProvider = Provider<HazardApi>((ref) => HazardApi());
final hazardCacheProvider =
    Provider<HazardCache>((ref) => HazardCache(ref.watch(sharedPrefsProvider)));

/// "What threatens where I am?" — the app's home tab.
///
/// The app used to open on a map of eight river basins, which answered one
/// question for eight places. This asks the question people actually have, for
/// anywhere, using the same assessment as the web dashboard.
class MyAreaScreen extends ConsumerStatefulWidget {
  const MyAreaScreen({super.key});

  @override
  ConsumerState<MyAreaScreen> createState() => _MyAreaScreenState();
}

class _MyAreaScreenState extends ConsumerState<MyAreaScreen> {
  Place? _place;
  Map<String, dynamic>? _profile;
  DateTime? _savedAt;
  bool _loading = false;
  bool _locating = false;
  String? _error;
  int _requestId = 0;

  final _searchController = TextEditingController();
  Timer? _debounce;
  List<Place> _results = [];
  bool _searching = false;

  static const _examples = [
    Place(latitude: 4.74, longitude: 45.2, name: 'Beledweyne', country: 'Somalia', countryCode: 'so'),
    Place(latitude: -1.2864, longitude: 36.8172, name: 'Nairobi', country: 'Kenya', countryCode: 'ke'),
    Place(latitude: -6.2088, longitude: 106.8456, name: 'Jakarta', country: 'Indonesia', countryCode: 'id'),
    Place(latitude: 14.5995, longitude: 120.9842, name: 'Manila', country: 'Philippines', countryCode: 'ph'),
  ];

  @override
  void initState() {
    super.initState();
    final cache = ref.read(hazardCacheProvider);
    _place = cache.place;
    _profile = cache.profile;
    _savedAt = cache.savedAt;
    if (_place != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _load(_place!));
    }
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _load(Place place) async {
    final id = ++_requestId;
    final cache = ref.read(hazardCacheProvider);
    final samePlace = _place?.latitude == place.latitude && _place?.longitude == place.longitude;
    setState(() {
      _place = place;
      _loading = true;
      _error = null;
      // Keep showing the old result only while refreshing the same place.
      if (!samePlace) _profile = null;
    });
    await cache.savePlace(place);

    try {
      final profile = await ref.read(hazardApiProvider).profile(place);
      if (!mounted || id != _requestId) return;
      final resolved = place.withServerLocation(
        profile['location'] is Map ? Map<String, dynamic>.from(profile['location']) : null,
      );
      setState(() {
        _profile = profile;
        _place = resolved;
        _savedAt = DateTime.now();
      });
      await cache.savePlace(resolved);
      await cache.saveProfile(profile);
    } catch (e) {
      if (!mounted || id != _requestId) return;
      setState(() => _error = HazardApi.describeError(e));
    } finally {
      if (mounted && id == _requestId) setState(() => _loading = false);
    }
  }

  Future<void> _useMyLocation() async {
    setState(() {
      _locating = true;
      _error = null;
    });
    try {
      if (!await Geolocator.isLocationServiceEnabled()) {
        throw 'Location is turned off. Turn it on, or search for your place.';
      }
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        throw 'Location access was not allowed. Search for your place instead.';
      }
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.low,
          timeLimit: Duration(seconds: 15),
        ),
      );
      _clearSearch();
      await _load(Place(
        latitude: double.parse(pos.latitude.toStringAsFixed(4)),
        longitude: double.parse(pos.longitude.toStringAsFixed(4)),
      ));
    } catch (e) {
      if (mounted) {
        setState(() => _error = e is String ? e : 'Could not find your location. Search instead.');
      }
    } finally {
      if (mounted) setState(() => _locating = false);
    }
  }

  void _onSearchChanged(String text) {
    _debounce?.cancel();
    final q = text.trim();
    if (q.length < 2) {
      setState(() {
        _results = [];
        _searching = false;
      });
      return;
    }
    setState(() => _searching = true);
    _debounce = Timer(const Duration(milliseconds: 350), () async {
      try {
        final found = await ref.read(hazardApiProvider).search(q);
        if (mounted && _searchController.text.trim() == q) setState(() => _results = found);
      } catch (_) {
        if (mounted) setState(() => _results = []);
      } finally {
        if (mounted) setState(() => _searching = false);
      }
    });
  }

  void _clearSearch() {
    _searchController.clear();
    FocusScope.of(context).unfocus();
    setState(() => _results = []);
  }

  void _pick(Place place) {
    _clearSearch();
    _load(place);
  }

  void _open(Map<String, dynamic> risk) {
    final profile = _profile;
    final place = _place;
    if (profile == null || place == null) return;
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => HazardDetailScreen(
          risk: risk,
          place: place,
          languages: List<String>.from(profile['languages'] ?? const ['en']),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final profile = _profile;
    final hazards = List<Map<String, dynamic>>.from(
      (profile?['hazards'] as List? ?? const []).map((h) => Map<String, dynamic>.from(h as Map)),
    );

    return Scaffold(
      appBar: AppBar(
        title: const Text('My area'),
        actions: const [AccountAction()],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          if (_place != null) await _load(_place!);
        },
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            _buildPicker(),
            if (_results.isNotEmpty) _buildResults(),
            const SizedBox(height: 12),
            if (_place != null)
              Text.rich(
                TextSpan(children: [
                  const TextSpan(text: 'Showing  ', style: TextStyle(color: AppColors.textMuted)),
                  TextSpan(
                    text: _place!.label,
                    style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.textPrimary),
                  ),
                ]),
                style: const TextStyle(fontSize: 14),
              ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              _Notice(
                message: _error!,
                onRetry: _place == null ? null : () => _load(_place!),
              ),
            ],
            const SizedBox(height: 12),
            if (_place == null && !_loading) _buildEmpty(),
            if (_loading && profile == null) ..._skeleton(),
            if (profile != null) ...[
              _SummaryBanner(
                level: profile['overall_risk'] as String? ?? 'LOW',
                headline: profile['headline'] as String? ?? '',
                updating: _loading,
                savedAt: _savedAt,
                partial: profile['partial'] == true,
                topHazard: hazards.isNotEmpty && hazards.first['risk_level'] != 'LOW'
                    ? hazards.first
                    : null,
                onOpenTop: _open,
              ),
              const SizedBox(height: 16),
              Text(
                '${hazards.length} hazards checked · tap one for what to do',
                style: const TextStyle(fontSize: 12.5, color: AppColors.textSecondary),
              ),
              const SizedBox(height: 8),
              for (final risk in hazards) _HazardTile(risk: risk, onTap: () => _open(risk)),
              if ((profile['screened_out'] as List? ?? const []).isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(
                  'Not relevant here: '
                  '${(profile['screened_out'] as List).map((h) => hazardMeta(h as String).short).join(', ')}. '
                  'Tayari checked and found no physical basis for these at this location.',
                  style: const TextStyle(fontSize: 12.5, color: AppColors.textMuted),
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildPicker() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          controller: _searchController,
          onChanged: _onSearchChanged,
          textInputAction: TextInputAction.search,
          onSubmitted: (_) {
            if (_results.isNotEmpty) _pick(_results.first);
          },
          decoration: InputDecoration(
            hintText: 'Search a town or city',
            prefixIcon: const Icon(Icons.search),
            suffixIcon: _searching
                ? const Padding(
                    padding: EdgeInsets.all(14),
                    child: SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
                  )
                : (_searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.close),
                        tooltip: 'Clear',
                        onPressed: _clearSearch,
                      )
                    : null),
          ),
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 48,
          child: _place == null
              ? FilledButton.icon(
                  onPressed: _locating ? null : _useMyLocation,
                  icon: const Icon(Icons.my_location),
                  label: Text(_locating ? 'Finding you…' : 'Use my location'),
                )
              : OutlinedButton.icon(
                  onPressed: _locating ? null : _useMyLocation,
                  icon: const Icon(Icons.my_location),
                  label: Text(_locating ? 'Finding you…' : 'Use my location'),
                ),
        ),
      ],
    );
  }

  Widget _buildResults() {
    return Card(
      margin: const EdgeInsets.only(top: 6),
      child: Column(
        children: [
          for (final p in _results)
            ListTile(
              leading: const Icon(Icons.place_outlined),
              title: Text(p.name ?? p.label),
              subtitle: Text(
                [p.admin1, p.country].whereType<String>().join(', '),
                style: const TextStyle(color: AppColors.textMuted),
              ),
              onTap: () => _pick(p),
            ),
        ],
      ),
    );
  }

  Widget _buildEmpty() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'What threatens where you are?',
          style: TextStyle(fontFamily: AppFonts.serif, fontSize: 22, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        const Text(
          'Tayari checks nine hazards — floods, earthquakes, tsunami, volcanoes, storms, '
          'heat, wildfire, drought and landslides — against live data, then tells you '
          'what to do about the ones that matter.',
          style: TextStyle(color: AppColors.textSecondary, height: 1.5),
        ),
        const SizedBox(height: 14),
        const Text('Or try one of these:', style: TextStyle(fontSize: 12.5, color: AppColors.textMuted)),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final p in _examples) ActionChip(label: Text(p.name!), onPressed: () => _pick(p)),
          ],
        ),
      ],
    );
  }

  List<Widget> _skeleton() => [
        for (final h in const [96.0, 72.0, 72.0, 72.0])
          Container(
            height: h,
            margin: const EdgeInsets.only(bottom: 8),
            decoration: BoxDecoration(
              color: AppColors.bgSecondary,
              borderRadius: BorderRadius.circular(10),
            ),
          ),
        const Center(
          child: Text('Checking nine hazards…', style: TextStyle(color: AppColors.textMuted)),
        ),
      ];
}

class _SummaryBanner extends StatelessWidget {
  final String level;
  final String headline;
  final bool updating;
  final bool partial;
  final DateTime? savedAt;
  final Map<String, dynamic>? topHazard;
  final void Function(Map<String, dynamic>) onOpenTop;

  const _SummaryBanner({
    required this.level,
    required this.headline,
    required this.updating,
    required this.partial,
    required this.savedAt,
    required this.topHazard,
    required this.onOpenTop,
  });

  @override
  Widget build(BuildContext context) {
    final color = AppColors.risk(level);
    final top = topHazard;
    return Semantics(
      liveRegion: true,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(12),
          border: Border(left: BorderSide(color: color, width: 5)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    kRiskWords[level] ?? level,
                    style: TextStyle(
                      fontFamily: AppFonts.serif,
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                      color: AppColors.riskText(level),
                    ),
                  ),
                ),
                if (updating)
                  const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
              ],
            ),
            const SizedBox(height: 6),
            Text(headline, style: const TextStyle(fontSize: 15, height: 1.45)),
            if (top != null) ...[
              const SizedBox(height: 10),
              FilledButton.tonal(
                onPressed: () => onOpenTop(top),
                child: Text('What to do about ${hazardMeta(top['hazard'] as String).short.toLowerCase()} →'),
              ),
            ],
            if (savedAt != null) ...[
              const SizedBox(height: 8),
              Text(
                'Updated ${_ago(savedAt!)}',
                style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
              ),
            ],
            if (partial)
              const Padding(
                padding: EdgeInsets.only(top: 4),
                child: Text(
                  'Some data feeds did not respond, so a hazard may be missing.',
                  style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
                ),
              ),
          ],
        ),
      ),
    );
  }

  static String _ago(DateTime t) {
    final d = DateTime.now().difference(t);
    if (d.inMinutes < 1) return 'just now';
    if (d.inMinutes < 60) return '${d.inMinutes} min ago';
    if (d.inHours < 24) return '${d.inHours} h ago';
    return '${d.inDays} days ago';
  }
}

class _HazardTile extends StatelessWidget {
  final Map<String, dynamic> risk;
  final VoidCallback onTap;
  const _HazardTile({required this.risk, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final meta = hazardMeta(risk['hazard'] as String);
    final level = risk['risk_level'] as String? ?? 'LOW';
    final onset = kOnsetLabels[risk['onset']] ?? (risk['onset'] as String? ?? '');
    final exposed = level == 'LOW' && ((risk['susceptibility'] as num?) ?? 0) >= 0.5;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(meta.icon, style: const TextStyle(fontSize: 24)),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(meta.label,
                              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15)),
                        ),
                        RiskBadge(level: level),
                      ],
                    ),
                    const SizedBox(height: 3),
                    Text(risk['headline'] as String? ?? '',
                        style: const TextStyle(color: AppColors.textSecondary, height: 1.35)),
                    const SizedBox(height: 4),
                    Text(
                      [onset, if (exposed) 'Exposed area, quiet right now'].join(' · '),
                      style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: AppColors.textMuted),
            ],
          ),
        ),
      ),
    );
  }
}

class RiskBadge extends StatelessWidget {
  final String level;
  const RiskBadge({super.key, required this.level});

  @override
  Widget build(BuildContext context) {
    final color = AppColors.risk(level);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        level,
        style: TextStyle(
          color: AppColors.riskText(level),
          fontSize: 11,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}

class _Notice extends StatelessWidget {
  final String message;
  final VoidCallback? onRetry;
  const _Notice({required this.message, this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 10, 8, 10),
      decoration: BoxDecoration(
        color: AppColors.riskHigh.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
        border: const Border(left: BorderSide(color: AppColors.riskHigh, width: 3)),
      ),
      child: Row(
        children: [
          Expanded(child: Text(message, style: const TextStyle(fontSize: 13.5))),
          if (onRetry != null) TextButton(onPressed: onRetry, child: const Text('Retry')),
        ],
      ),
    );
  }
}
