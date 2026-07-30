import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/db_provider.dart';
import '../theme.dart';

/// Opens the feedback sheet. Mirrors the web app's feedback modal: a required
/// 1–5 emoji opinion rating, an optional subject, an optional comment, and a
/// submit that goes to the backend (with a direct FormSubmit.co fallback so
/// feedback is never lost when the backend is cold or offline).
Future<void> showFeedbackSheet(BuildContext context) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: AppColors.paper,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
    ),
    builder: (_) => const _FeedbackSheet(),
  );
}

class _Emoji {
  final int value;
  final String icon;
  final String label;
  const _Emoji(this.value, this.icon, this.label);
}

const _emojis = <_Emoji>[
  _Emoji(1, '😠', 'Angry'),
  _Emoji(2, '😞', 'Sad'),
  _Emoji(3, '😐', 'Neutral'),
  _Emoji(4, '🙂', 'Happy'),
  _Emoji(5, '😄', 'Very happy'),
];

const _subjects = ['Bug', 'Suggestion', 'Other'];

class _FeedbackSheet extends ConsumerStatefulWidget {
  const _FeedbackSheet();

  @override
  ConsumerState<_FeedbackSheet> createState() => _FeedbackSheetState();
}

class _FeedbackSheetState extends ConsumerState<_FeedbackSheet> {
  int? _rating;
  String? _subject;
  final _commentController = TextEditingController();
  bool _submitting = false;
  bool _submitted = false;
  String? _error;

  @override
  void dispose() {
    _commentController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_rating == null) {
      setState(() => _error = 'Please select an opinion rating.');
      return;
    }
    setState(() {
      _error = null;
      _submitting = true;
    });

    try {
      await ref.read(apiClientProvider).submitFeedback(
            rating: _rating!,
            subject: _subject,
            comment: _commentController.text.trim(),
          );
      if (!mounted) return;
      setState(() => _submitted = true);
      // Let the "thank you" state linger briefly, then close.
      await Future.delayed(const Duration(seconds: 2));
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _submitting = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    // Sit above the keyboard when the comment field is focused.
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    return Padding(
      padding: EdgeInsets.only(bottom: bottomInset),
      child: SafeArea(
        top: false,
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
          child: _submitted ? _buildSuccess() : _buildForm(),
        ),
      ),
    );
  }

  Widget _buildSuccess() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: const [
        SizedBox(height: 12),
        CircleAvatar(
          radius: 26,
          backgroundColor: AppColors.riskLow,
          child: Icon(Icons.check, color: Colors.white, size: 30),
        ),
        SizedBox(height: 16),
        Text(
          'Thank you for your feedback!',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        SizedBox(height: 20),
      ],
    );
  }

  Widget _buildForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // Drag handle.
        Center(
          child: Container(
            width: 40,
            height: 4,
            margin: const EdgeInsets.only(bottom: 12),
            decoration: BoxDecoration(
              color: AppColors.borderStrong,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
        ),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'Your feedback',
              style: TextStyle(
                fontFamily: AppFonts.serif,
                fontSize: 20,
                fontWeight: FontWeight.w600,
              ),
            ),
            IconButton(
              icon: const Icon(Icons.close, size: 22),
              color: AppColors.textMuted,
              tooltip: 'Close',
              onPressed: () => Navigator.of(context).pop(),
            ),
          ],
        ),
        const SizedBox(height: 4),

        _label('What is your opinion of the app?', required: true),
        const SizedBox(height: 8),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            for (final e in _emojis) _emojiButton(e),
          ],
        ),
        const SizedBox(height: 20),

        _label('Please select a subject:'),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: [
            for (final s in _subjects) _subjectChip(s),
          ],
        ),
        const SizedBox(height: 20),

        _label('Would you like to add a comment?'),
        const SizedBox(height: 8),
        TextField(
          controller: _commentController,
          minLines: 3,
          maxLines: 5,
          textCapitalization: TextCapitalization.sentences,
          decoration: const InputDecoration(
            hintText: 'Tell us what worked or what to improve…',
          ),
        ),

        if (_error != null) ...[
          const SizedBox(height: 12),
          Text(
            _error!,
            style: const TextStyle(color: AppColors.riskHigh, fontSize: 13),
          ),
        ],

        const SizedBox(height: 20),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            onPressed: (_submitting || _rating == null) ? null : _submit,
            child: _submitting
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Text('Send feedback'),
          ),
        ),
        const SizedBox(height: 14),
        const Center(
          child: Text.rich(
            TextSpan(
              text: 'Powered by ',
              style: TextStyle(color: AppColors.textMuted, fontSize: 12),
              children: [
                TextSpan(
                  text: 'LaunchPixel',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _label(String text, {bool required = false}) {
    return Text.rich(
      TextSpan(
        text: text,
        style: const TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          color: AppColors.textPrimary,
        ),
        children: [
          if (required)
            const TextSpan(
              text: ' *',
              style: TextStyle(color: AppColors.riskHigh),
            ),
        ],
      ),
    );
  }

  Widget _emojiButton(_Emoji e) {
    final selected = _rating == e.value;
    return Semantics(
      button: true,
      selected: selected,
      label: e.label,
      child: Tooltip(
        message: e.label,
        child: GestureDetector(
          onTap: () => setState(() => _rating = e.value),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 120),
            width: 52,
            height: 52,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: selected
                  ? AppColors.accent.withValues(alpha: 0.12)
                  : AppColors.surface,
              shape: BoxShape.circle,
              border: Border.all(
                color: selected ? AppColors.accent : AppColors.border,
                width: selected ? 2 : 1,
              ),
            ),
            child: Text(
              e.icon,
              style: TextStyle(fontSize: selected ? 26 : 22),
            ),
          ),
        ),
      ),
    );
  }

  Widget _subjectChip(String subject) {
    final selected = _subject == subject;
    return ChoiceChip(
      label: Text(subject),
      selected: selected,
      onSelected: (_) =>
          setState(() => _subject = selected ? null : subject),
      showCheckmark: false,
      backgroundColor: AppColors.surface,
      selectedColor: AppColors.accent.withValues(alpha: 0.14),
      side: BorderSide(
        color: selected ? AppColors.accent : AppColors.border,
      ),
      labelStyle: TextStyle(
        color: selected ? AppColors.accent : AppColors.textSecondary,
        fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
      ),
    );
  }
}
