import 'package:supabase_flutter/supabase_flutter.dart';

/// Thin wrapper over Supabase Auth (GoTrue). Sign-in is entirely optional in
/// Tayari — the app works fully signed-out — so every call first checks that
/// Supabase actually started. Auth talks to Supabase over HTTPS and is
/// independent of the backend API and its database, so it keeps working even
/// when the reports/forecast backend is cold or down.
class AuthService {
  /// Set to true by `main()` once `Supabase.initialize` succeeds. When false,
  /// the account UI is hidden and every method here throws a friendly error.
  static bool initialized = false;

  SupabaseClient get _client => Supabase.instance.client;

  /// Fires whenever the session changes (sign-in, sign-out, token refresh).
  /// Supabase emits the current session immediately on subscribe, so a stream
  /// listener always gets the starting state.
  Stream<User?> get userChanges {
    if (!initialized) return const Stream.empty();
    return _client.auth.onAuthStateChange.map((s) => s.session?.user);
  }

  /// The signed-in user, or null when signed out / auth unavailable.
  User? get currentUser => initialized ? _client.auth.currentUser : null;

  /// A human label for the signed-in user — their display name if they set one
  /// at sign-up, otherwise their email.
  String? get displayLabel {
    final u = currentUser;
    if (u == null) return null;
    final name = u.userMetadata?['display_name'];
    if (name is String && name.trim().isNotEmpty) return name.trim();
    return u.email;
  }

  Future<void> signIn(String email, String password) async {
    _ensureReady();
    await _client.auth.signInWithPassword(email: email.trim(), password: password);
  }

  /// Creates an account. The project requires email confirmation, so a
  /// confirmation link is sent and no session exists until the user clicks it —
  /// the caller shows a "check your email" message accordingly.
  /// Returns true when a session was created immediately (confirmation off).
  Future<bool> signUp(String email, String password, String? displayName) async {
    _ensureReady();
    final res = await _client.auth.signUp(
      email: email.trim(),
      password: password,
      data: (displayName != null && displayName.trim().isNotEmpty)
          ? {'display_name': displayName.trim()}
          : null,
    );
    return res.session != null;
  }

  /// Sends a password-reset link. Without a mobile deep link configured, the
  /// link opens the Tayari web app's reset page — same flow as the website.
  Future<void> resetPassword(String email) async {
    _ensureReady();
    await _client.auth.resetPasswordForEmail(email.trim());
  }

  Future<void> signOut() async {
    _ensureReady();
    await _client.auth.signOut();
  }

  void _ensureReady() {
    if (!initialized) {
      throw const AuthException('Sign-in is unavailable right now.');
    }
  }
}
