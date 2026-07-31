import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../services/auth_service.dart';

/// Singleton auth wrapper.
final authServiceProvider = Provider<AuthService>((ref) => AuthService());

/// The current signed-in user (null when signed out or auth is unavailable).
/// Backed by Supabase's auth-state stream so the app bar updates the instant a
/// sign-in or sign-out completes. Seeded with the restored session so a
/// returning user shows as signed-in on first frame.
final authUserProvider = StreamProvider<User?>((ref) {
  final auth = ref.watch(authServiceProvider);
  if (!AuthService.initialized) return Stream.value(null);
  return auth.userChanges;
});
