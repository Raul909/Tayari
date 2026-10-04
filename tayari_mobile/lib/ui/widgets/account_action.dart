import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/auth_provider.dart';
import '../../services/auth_service.dart';
import '../theme.dart';
import 'auth_sheet.dart';

/// App-bar account button. Sign-in is optional, so this only appears when
/// Supabase started. Signed out it opens the sign-in dialog; signed in it
/// shows the account and a sign-out action.
class AccountAction extends ConsumerWidget {
  const AccountAction({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Auth unavailable (Supabase didn't start) → no account UI at all.
    if (!AuthService.initialized) return const SizedBox.shrink();

    final user = ref.watch(authUserProvider).value;

    if (user == null) {
      return IconButton(
        icon: const Icon(Icons.account_circle_outlined),
        tooltip: 'Sign in',
        onPressed: () => showAuthSheet(context),
      );
    }

    final label = ref.read(authServiceProvider).displayLabel ?? 'Signed in';
    return PopupMenuButton<String>(
      tooltip: 'Account',
      icon: const Icon(Icons.account_circle, color: AppColors.accent),
      onSelected: (value) async {
        if (value == 'signout') {
          try {
            await ref.read(authServiceProvider).signOut();
            if (context.mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Signed out.')),
              );
            }
          } catch (_) {
            if (context.mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Could not sign out. Try again.')),
              );
            }
          }
        }
      },
      itemBuilder: (context) => [
        PopupMenuItem<String>(
          enabled: false,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Signed in as',
                  style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
              const SizedBox(height: 2),
              Text(
                label,
                style: const TextStyle(
                  fontSize: 13.5,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
        ),
        const PopupMenuDivider(),
        const PopupMenuItem<String>(
          value: 'signout',
          child: Row(
            children: [
              Icon(Icons.logout, size: 18, color: AppColors.textSecondary),
              SizedBox(width: 10),
              Text('Sign out'),
            ],
          ),
        ),
      ],
    );
  }
}
