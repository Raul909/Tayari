import 'package:flutter/material.dart';

/// Tayari palette — calm, warm, paper-toned. Mirrors the web dashboard:
/// one terracotta accent, muted (but unambiguous) risk colours, no glow.
class AppColors {
  static const paper = Color(0xFFFAF9F6);
  static const bgSecondary = Color(0xFFF3F1EA);
  static const surface = Color(0xFFFFFFFF);
  static const surfaceSunken = Color(0xFFF6F4EE);

  static const textPrimary = Color(0xFF23211C);
  static const textSecondary = Color(0xFF6B6558);
  static const textMuted = Color(0xFF938C7E);

  static const accent = Color(0xFFB7562F);

  static const border = Color(0xFFE5E1D8);
  static const borderStrong = Color(0xFFD8D3C7);

  static const riskLow = Color(0xFF3F7D53);
  static const riskModerate = Color(0xFFB0812C);
  static const riskHigh = Color(0xFFC0432B);
  static const riskExtreme = Color(0xFF83291A);

  /// Map a backend risk level string to its colour.
  static Color risk(String? level) {
    switch ((level ?? '').toUpperCase()) {
      case 'EXTREME':
        return riskExtreme;
      case 'HIGH':
        return riskHigh;
      case 'MODERATE':
        return riskModerate;
      default:
        return riskLow;
    }
  }
}

/// Font families. We use the platform's built-in serif and monospace faces
/// (no bundled assets — keeps the APK small and quick to render on low-end
/// devices) to echo the web dashboard: a serif brand/headline, monospaced
/// figures.
class AppFonts {
  static const serif = 'serif';
  static const mono = 'monospace';
}

ThemeData buildTayariTheme() {
  final base = ThemeData(
    useMaterial3: true,
    brightness: Brightness.light,
  );

  return base.copyWith(
    scaffoldBackgroundColor: AppColors.paper,
    colorScheme: base.colorScheme.copyWith(
      primary: AppColors.accent,
      secondary: AppColors.accent,
      surface: AppColors.surface,
      onSurface: AppColors.textPrimary,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.paper,
      foregroundColor: AppColors.textPrimary,
      elevation: 0,
      scrolledUnderElevation: 0.5,
      centerTitle: false,
      titleTextStyle: TextStyle(
        color: AppColors.textPrimary,
        fontFamily: AppFonts.serif,
        fontSize: 20,
        fontWeight: FontWeight.w600,
      ),
    ),
    textTheme: base.textTheme.apply(
      bodyColor: AppColors.textPrimary,
      displayColor: AppColors.textPrimary,
    ),
    dividerColor: AppColors.border,
    iconTheme: const IconThemeData(color: AppColors.textSecondary),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.accent,
        foregroundColor: Colors.white,
        elevation: 0,
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 20),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surface,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: AppColors.borderStrong),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: AppColors.borderStrong),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: AppColors.accent, width: 1.5),
      ),
      labelStyle: const TextStyle(color: AppColors.textSecondary),
    ),
    snackBarTheme: const SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: AppColors.textPrimary,
      contentTextStyle: TextStyle(color: AppColors.paper),
    ),
  );
}
