import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/db_provider.dart';
import '../theme.dart';

/// Follow-up chat about a basin's advisory, mirroring the web dashboard: an
/// expandable thread capped at 5 questions per session, with the remaining
/// count shown. Online-only (the backend runs the model); when offline a send
/// fails gracefully with an inline notice.
///
/// Give this a [ValueKey] of basin+role+language so the thread resets whenever
/// the advisory it's about changes.
class AdvisoryChat extends ConsumerStatefulWidget {
  final String basinId;
  final String role;
  final String language;

  const AdvisoryChat({
    super.key,
    required this.basinId,
    required this.role,
    required this.language,
  });

  @override
  ConsumerState<AdvisoryChat> createState() => _AdvisoryChatState();
}

class _ChatMsg {
  final String role; // 'user' | 'ai'
  final String content;
  const _ChatMsg(this.role, this.content);
}

class _AdvisoryChatState extends ConsumerState<AdvisoryChat> {
  bool _open = false;
  final List<_ChatMsg> _messages = [];
  int _remaining = 5;
  bool _sending = false;
  final _controller = TextEditingController();
  // Monotonic token so a slow reply for a thread the user has already reset
  // (by changing role/language) can't land in the current one.
  int _reqId = 0;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _sending || _remaining <= 0) return;

    // Prior turns, before this message, in the shape the backend expects.
    final session = [
      for (final m in _messages) {'role': m.role, 'content': m.content},
    ];

    setState(() {
      _messages.add(_ChatMsg('user', text));
      _controller.clear();
      _sending = true;
    });
    final reqId = ++_reqId;

    try {
      final res = await ref.read(apiClientProvider).sendChatMessage(
            widget.basinId,
            text,
            role: widget.role,
            language: widget.language,
            sessionMessages: session,
          );
      if (!mounted || reqId != _reqId) return;
      setState(() {
        _messages.add(_ChatMsg('ai', (res['reply'] ?? '').toString().trim()));
        _remaining =
            (res['messages_remaining'] as num?)?.toInt() ?? (_remaining - 1);
      });
    } catch (_) {
      if (!mounted || reqId != _reqId) return;
      setState(() {
        _messages.add(const _ChatMsg(
          'ai',
          "Sorry, I couldn't respond just now. Check your connection and try "
              'again.',
        ));
      });
    } finally {
      if (mounted && reqId == _reqId) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            onPressed: () => setState(() => _open = !_open),
            icon: Icon(
              _open ? Icons.close : Icons.chat_bubble_outline,
              size: 16,
            ),
            label: Text(_open ? 'Hide chat' : 'Ask about this advisory'),
            style: TextButton.styleFrom(
              foregroundColor: AppColors.accent,
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            ),
          ),
        ),
        if (_open)
          Container(
            width: double.infinity,
            margin: const EdgeInsets.only(top: 4),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.surfaceSunken,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (_messages.isEmpty && !_sending)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 8),
                    child: Text(
                      'Ask a question about this advisory — for example, '
                      '"What should I do with my livestock?"',
                      style: TextStyle(
                        color: AppColors.textMuted,
                        fontSize: 13,
                        height: 1.4,
                      ),
                    ),
                  ),
                for (final m in _messages) _bubble(m),
                if (_sending) _thinkingBubble(),
                const SizedBox(height: 8),
                _inputRow(),
                const SizedBox(height: 6),
                Text(
                  '$_remaining of 5 questions remaining',
                  style: const TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }

  Widget _bubble(_ChatMsg m) {
    final isUser = m.role == 'user';
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.72,
        ),
        decoration: BoxDecoration(
          color: isUser ? AppColors.accent : AppColors.surface,
          borderRadius: BorderRadius.circular(12),
          border: isUser ? null : Border.all(color: AppColors.border),
        ),
        child: Text(
          m.content,
          style: TextStyle(
            color: isUser ? Colors.white : AppColors.textPrimary,
            fontSize: 14,
            height: 1.4,
          ),
        ),
      ),
    );
  }

  Widget _thinkingBubble() {
    return const Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: EdgeInsets.symmetric(vertical: 6, horizontal: 4),
        child: Text(
          'Thinking…',
          style: TextStyle(
            color: AppColors.textMuted,
            fontSize: 13,
            fontStyle: FontStyle.italic,
          ),
        ),
      ),
    );
  }

  Widget _inputRow() {
    final disabled = _sending || _remaining <= 0;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Expanded(
          child: TextField(
            controller: _controller,
            enabled: !disabled,
            minLines: 1,
            maxLines: 3,
            textInputAction: TextInputAction.send,
            onSubmitted: (_) => _send(),
            decoration: InputDecoration(
              isDense: true,
              hintText: _remaining <= 0
                  ? 'Question limit reached'
                  : 'Ask a question…',
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            ),
          ),
        ),
        const SizedBox(width: 8),
        SizedBox(
          height: 42,
          child: ElevatedButton(
            onPressed: disabled ? null : _send,
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 16),
            ),
            child: const Text('Send'),
          ),
        ),
      ],
    );
  }
}
