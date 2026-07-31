import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../providers/auth_provider.dart';
import '../theme.dart';

/// Opens the optional sign-in dialog. Mirrors the web app's auth modal: a
/// centered card with Sign In / Create Account tabs, a Forgot Password flow,
/// and a small close (×) in the top-right — nothing is required to use Tayari,
/// so it's freely dismissible (tap outside or the ×).
Future<void> showAuthSheet(BuildContext context) {
  return showDialog<void>(
    context: context,
    barrierDismissible: true,
    builder: (_) => const _AuthDialog(),
  );
}

enum _View { login, register, forgot, resetSent }

class _AuthDialog extends ConsumerStatefulWidget {
  const _AuthDialog();

  @override
  ConsumerState<_AuthDialog> createState() => _AuthDialogState();
}

class _AuthDialogState extends ConsumerState<_AuthDialog> {
  _View _view = _View.login;
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _nameController = TextEditingController();
  bool _loading = false;
  String? _error;
  String? _notice; // success/info banner (e.g. "confirm your email")

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  void _switchView(_View next) {
    setState(() {
      _view = next;
      _error = null;
      _notice = null;
    });
  }

  Future<void> _submit() async {
    final email = _emailController.text.trim();
    final password = _passwordController.text;

    // Light client-side checks so we don't round-trip obvious mistakes.
    if (email.isEmpty || !email.contains('@')) {
      setState(() => _error = 'Enter a valid email address.');
      return;
    }
    if (_view != _View.forgot && password.length < 6) {
      setState(() => _error = 'Password must be at least 6 characters.');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
      _notice = null;
    });

    final auth = ref.read(authServiceProvider);
    try {
      switch (_view) {
        case _View.login:
          await auth.signIn(email, password);
          if (mounted) Navigator.of(context).pop();
          return;
        case _View.register:
          final hasSession =
              await auth.signUp(email, password, _nameController.text);
          if (!mounted) return;
          if (hasSession) {
            Navigator.of(context).pop();
            return;
          }
          // Email confirmation required — keep the dialog open with guidance.
          setState(() {
            _notice =
                'Account created. Check $email for a confirmation link, then sign in.';
            _view = _View.login;
            _passwordController.clear();
          });
        case _View.forgot:
          await auth.resetPassword(email);
          if (mounted) setState(() => _view = _View.resetSent);
        case _View.resetSent:
          break;
      }
    } on AuthException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } catch (e) {
      if (mounted) {
        setState(() => _error =
            'Something went wrong. Check your connection and try again.');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: AppColors.paper,
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 420),
        child: SingleChildScrollView(
          child: Stack(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(22, 24, 22, 22),
                child: _view == _View.resetSent
                    ? _buildResetSent()
                    : _buildForm(),
              ),
              // Small close (×) in the top-right, like the web modal.
              Positioned(
                top: 4,
                right: 4,
                child: IconButton(
                  icon: const Icon(Icons.close, size: 22),
                  color: AppColors.textMuted,
                  tooltip: 'Close',
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildForm() {
    final isLogin = _view == _View.login;
    final isRegister = _view == _View.register;
    final isForgot = _view == _View.forgot;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        const Text(
          'Tayari account',
          style: TextStyle(
            fontFamily: AppFonts.serif,
            fontSize: 20,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 2),
        const Text(
          'Optional — sign in to sync your reports and preferences.',
          style: TextStyle(color: AppColors.textMuted, fontSize: 12.5),
        ),
        const SizedBox(height: 16),

        // Sign In / Create Account tabs (hidden on the forgot-password view).
        if (!isForgot) ...[
          Row(
            children: [
              _tab('Sign In', isLogin, () => _switchView(_View.login)),
              const SizedBox(width: 8),
              _tab('Create Account', isRegister,
                  () => _switchView(_View.register)),
            ],
          ),
          const SizedBox(height: 18),
        ],

        if (isForgot)
          const Padding(
            padding: EdgeInsets.only(bottom: 14),
            child: Text(
              "Enter your email and we'll send you a link to reset your password.",
              style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
            ),
          ),

        if (_notice != null) _banner(_notice!, ok: true),
        if (_error != null) _banner(_error!, ok: false),

        if (isRegister) ...[
          _fieldLabel('Display name'),
          const SizedBox(height: 6),
          TextField(
            controller: _nameController,
            textCapitalization: TextCapitalization.words,
            decoration: const InputDecoration(hintText: 'e.g. Ayen from Bor'),
          ),
          const SizedBox(height: 14),
        ],

        _fieldLabel('Email'),
        const SizedBox(height: 6),
        TextField(
          controller: _emailController,
          keyboardType: TextInputType.emailAddress,
          autofillHints: const [AutofillHints.email],
          decoration: const InputDecoration(hintText: 'you@example.com'),
        ),

        if (!isForgot) ...[
          const SizedBox(height: 14),
          _fieldLabel('Password'),
          const SizedBox(height: 6),
          TextField(
            controller: _passwordController,
            obscureText: true,
            decoration: const InputDecoration(hintText: 'At least 6 characters'),
            onSubmitted: (_) => _loading ? null : _submit(),
          ),
          if (isLogin)
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: () => _switchView(_View.forgot),
                style: TextButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  minimumSize: Size.zero,
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  foregroundColor: AppColors.accent,
                ),
                child: const Text('Forgot password?',
                    style: TextStyle(fontSize: 12.5)),
              ),
            ),
        ],

        const SizedBox(height: 18),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            onPressed: _loading ? null : _submit,
            child: _loading
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: Colors.white),
                  )
                : Text(isLogin
                    ? 'Sign In'
                    : isRegister
                        ? 'Create Account'
                        : 'Send reset link'),
          ),
        ),

        if (isForgot) ...[
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: _loading ? null : () => _switchView(_View.login),
              child: const Text('Back to Sign In'),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildResetSent() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        const SizedBox(height: 8),
        const CircleAvatar(
          radius: 26,
          backgroundColor: AppColors.riskLow,
          child: Icon(Icons.mark_email_read_outlined,
              color: Colors.white, size: 28),
        ),
        const SizedBox(height: 16),
        const Text(
          'Check your email',
          style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 8),
        Text(
          "We've sent a password reset link to ${_emailController.text.trim()}.",
          textAlign: TextAlign.center,
          style: const TextStyle(color: AppColors.textSecondary, fontSize: 13.5),
        ),
        const SizedBox(height: 20),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton(
            onPressed: () => _switchView(_View.login),
            child: const Text('Back to Sign In'),
          ),
        ),
      ],
    );
  }

  Widget _tab(String label, bool active, VoidCallback onTap) {
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: active
                ? AppColors.accent.withValues(alpha: 0.12)
                : AppColors.surface,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: active ? AppColors.accent : AppColors.border,
              width: active ? 1.5 : 1,
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              color: active ? AppColors.accent : AppColors.textSecondary,
              fontWeight: active ? FontWeight.w700 : FontWeight.w500,
              fontSize: 13.5,
            ),
          ),
        ),
      ),
    );
  }

  Widget _fieldLabel(String text) => Text(
        text,
        style: const TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w600,
          color: AppColors.textPrimary,
        ),
      );

  Widget _banner(String text, {required bool ok}) {
    final color = ok ? AppColors.riskLow : AppColors.riskHigh;
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(
        text,
        style: TextStyle(color: color, fontSize: 12.5, height: 1.35),
      ),
    );
  }
}
