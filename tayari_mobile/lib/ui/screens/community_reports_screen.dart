import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/basin_provider.dart';
import '../../providers/db_provider.dart';
import '../../providers/prefs_provider.dart';
import '../../services/api_client.dart';
import '../theme.dart';

/// Live feed of community reports from all basins, with advice threads so
/// coordinators and neighbours can respond with concrete guidance.
class CommunityReportsScreen extends ConsumerStatefulWidget {
  const CommunityReportsScreen({super.key});

  @override
  ConsumerState<CommunityReportsScreen> createState() =>
      _CommunityReportsScreenState();
}

class _CommunityReportsScreenState
    extends ConsumerState<CommunityReportsScreen> {
  List<Map<String, dynamic>>? _reports;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await ref.read(apiClientProvider).getReports();
      if (!mounted) return;
      setState(() {
        _reports = data.cast<Map<String, dynamic>>().reversed.toList();
        _error = null;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = 'Could not load reports. Check your connection and retry.';
      });
    }
  }

  void _replaceReport(Map<String, dynamic> updated) {
    setState(() {
      _reports = _reports
          ?.map((r) => r['id'] == updated['id'] ? updated : r)
          .toList();
    });
  }

  @override
  Widget build(BuildContext context) {
    // Map basin ids to their human-readable names from the local cache.
    final basinNames = <String, String>{
      for (final b in ref.watch(basinsStreamProvider).value ?? [])
        b.basinId as String: b.name as String,
    };

    return Scaffold(
      appBar: AppBar(title: const Text('Community reports')),
      body: _error != null
          ? Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(_error!,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: AppColors.textSecondary)),
                  const SizedBox(height: 12),
                  ElevatedButton(onPressed: _load, child: const Text('Retry')),
                ],
              ),
            )
          : _reports == null
              ? const Center(child: CircularProgressIndicator())
              : _reports!.isEmpty
                  ? const Center(
                      child: Text(
                        'No reports yet.\nBe the first to report conditions in your basin.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: AppColors.textMuted),
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.separated(
                        padding: const EdgeInsets.all(12),
                        itemCount: _reports!.length,
                        separatorBuilder: (_, _) => const SizedBox(height: 10),
                        itemBuilder: (context, index) => _ReportCard(
                          report: _reports![index],
                          basinName: basinNames[_reports![index]['basin_id']] ??
                              (_reports![index]['basin_id'] ?? '').toString(),
                          onUpdated: _replaceReport,
                        ),
                      ),
                    ),
    );
  }
}

const _statusLabels = {
  'water_rising': 'Water rising',
  'road_flooded': 'Road flooded',
  'evacuating': 'Evacuating',
  'all_clear': 'All clear',
};

Color _statusColor(String? status) {
  switch (status) {
    case 'evacuating':
      return AppColors.riskExtreme;
    case 'road_flooded':
      return AppColors.riskHigh;
    case 'water_rising':
      return AppColors.riskModerate;
    case 'all_clear':
      return AppColors.riskLow;
    default:
      return AppColors.textMuted;
  }
}

class _ReportCard extends ConsumerStatefulWidget {
  final Map<String, dynamic> report;
  final String basinName;
  final void Function(Map<String, dynamic>) onUpdated;

  const _ReportCard({
    required this.report,
    required this.basinName,
    required this.onUpdated,
  });

  @override
  ConsumerState<_ReportCard> createState() => _ReportCardState();
}

class _ReportCardState extends ConsumerState<_ReportCard> {
  final _adviceController = TextEditingController();
  bool _showAdviceField = false;
  bool _sending = false;

  @override
  void dispose() {
    _adviceController.dispose();
    super.dispose();
  }

  Future<void> _sendAdvice() async {
    final message = _adviceController.text.trim();
    if (message.length < 2) return;

    setState(() => _sending = true);
    try {
      final prefs = ref.read(userPrefsProvider);
      final updated = await ref.read(apiClientProvider).postAdvice(
            widget.report['id'] as int,
            message: message,
            authorRole: prefs.role,
          );
      widget.onUpdated(updated);
      _adviceController.clear();
      if (mounted) setState(() => _showAdviceField = false);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text('Could not send advice. Try again when online.')),
        );
      }
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final report = widget.report;
    final status = report['status'] as String?;
    final color = _statusColor(status);
    final photoUrl = report['photo_url'] != null
        ? '${ApiClient.assetBaseUrl}${report['photo_url']}'
        : null;
    final advice = (report['advice'] as List?) ?? [];
    final submittedAt =
        DateTime.tryParse(report['submitted_at']?.toString() ?? '');

    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (photoUrl != null)
            ClipRRect(
              borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
              child: Image.network(
                photoUrl,
                height: 160,
                width: double.infinity,
                fit: BoxFit.cover,
                errorBuilder: (_, _, _) => const SizedBox.shrink(),
              ),
            ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: color.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: color),
                      ),
                      child: Text(
                        _statusLabels[status] ?? status ?? 'Report',
                        style: TextStyle(
                          color: color,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    const Spacer(),
                    if (submittedAt != null)
                      Text(
                        '${submittedAt.day}/${submittedAt.month} '
                        '${submittedAt.hour.toString().padLeft(2, '0')}:'
                        '${submittedAt.minute.toString().padLeft(2, '0')}',
                        style: const TextStyle(
                            color: AppColors.textMuted, fontSize: 11),
                      ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  widget.basinName,
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                  ),
                ),
                if ((report['description'] ?? '').toString().isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      report['description'].toString(),
                      style: const TextStyle(
                          color: AppColors.textSecondary, fontSize: 13),
                    ),
                  ),
                if ((report['reporter_name'] ?? '').toString().isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      'by ${report['reporter_name']}',
                      style: const TextStyle(
                          color: AppColors.textMuted, fontSize: 12),
                    ),
                  ),
                if (advice.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  for (final a in advice)
                    Container(
                      width: double.infinity,
                      margin: const EdgeInsets.only(bottom: 6),
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: AppColors.surfaceSunken,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AppColors.border),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            (a['message'] ?? '').toString(),
                            style: const TextStyle(
                                fontSize: 13, color: AppColors.textPrimary),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            '💬 ${a['author_name'] ?? a['author_role'] ?? 'Responder'}',
                            style: const TextStyle(
                                fontSize: 11, color: AppColors.textMuted),
                          ),
                        ],
                      ),
                    ),
                ],
                const SizedBox(height: 8),
                if (_showAdviceField)
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _adviceController,
                          decoration: const InputDecoration(
                            hintText: 'Share advice or a safe route…',
                            isDense: true,
                          ),
                          minLines: 1,
                          maxLines: 3,
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton(
                        icon: _sending
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child:
                                    CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.send, color: AppColors.accent),
                        onPressed: _sending ? null : _sendAdvice,
                      ),
                    ],
                  )
                else
                  TextButton.icon(
                    onPressed: () => setState(() => _showAdviceField = true),
                    icon: const Icon(Icons.forum_outlined, size: 16),
                    label: Text(
                      advice.isEmpty
                          ? 'Give advice'
                          : 'Give advice (${advice.length})',
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
