import 'package:flutter/material.dart';

import 'theme.dart';

/// Labels, icons and colours for the nine hazards, mirrored from the backend
/// registry (and the web app's `HAZARD_META`) so the first frame has them
/// without a request.
///
/// Icons are Material icons, the same family the web app draws, so a hazard
/// looks the same on both. Material has no earthquake glyph in Flutter's
/// built-in set, so that one is drawn by [HazardIcon] instead — `icon` is null
/// for it.
class HazardMeta {
  final String label;
  final String short;
  final IconData? icon;
  final Color color;
  const HazardMeta(this.label, this.short, this.icon, this.color);
}

const kHazardMeta = <String, HazardMeta>{
  'flood': HazardMeta('River flooding', 'Flood', Icons.flood_outlined, Color(0xFF2E6F8E)),
  'earthquake': HazardMeta('Earthquake', 'Quake', null, Color(0xFF8A5A2B)),
  'tsunami': HazardMeta('Tsunami', 'Tsunami', Icons.tsunami_outlined, Color(0xFF1F5F73)),
  'volcano': HazardMeta('Volcanic activity', 'Volcano', Icons.volcano_outlined, Color(0xFFA2412A)),
  'cyclone': HazardMeta('Cyclone & severe storm', 'Storm', Icons.cyclone_outlined, Color(0xFF4C5B8C)),
  'extreme_heat': HazardMeta('Extreme heat', 'Heat', Icons.thermostat_outlined, Color(0xFFC2603A)),
  'wildfire':
      HazardMeta('Wildfire weather', 'Wildfire', Icons.local_fire_department_outlined, Color(0xFFB4501F)),
  'drought': HazardMeta('Drought', 'Drought', Icons.wb_sunny_outlined, Color(0xFF9A7B3F)),
  'landslide': HazardMeta('Landslide', 'Landslide', Icons.landslide_outlined, Color(0xFF6B5B45)),
};

HazardMeta hazardMeta(String hazard) =>
    kHazardMeta[hazard] ?? HazardMeta(hazard, hazard, Icons.warning_amber_outlined, const Color(0xFF6B6558));

/// A hazard's icon in its colour, on a plain tile.
class HazardIcon extends StatelessWidget {
  final String hazard;
  final double size;
  const HazardIcon(this.hazard, {super.key, this.size = 22});

  @override
  Widget build(BuildContext context) {
    final meta = hazardMeta(hazard);
    final glyph = meta.icon != null
        ? Icon(meta.icon, size: size, color: meta.color)
        : CustomPaint(size: Size.square(size), painter: _QuakePainter(meta.color));
    return Container(
      width: size + 14,
      height: size + 14,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: AppColors.surfaceSunken,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.border),
      ),
      child: ExcludeSemantics(child: glyph),
    );
  }
}

/// Material Symbols "earthquake" (Apache-2.0), a seismograph trace, converted
/// from its SVG path onto Flutter's 24-unit icon grid.
class _QuakePainter extends CustomPainter {
  final Color color;
  const _QuakePainter(this.color);

  @override
  void paint(Canvas canvas, Size size) {
    final scale = size.width / 24;
    canvas.scale(scale);
    final path = Path()
      ..moveTo(9, 22)
      ..quadraticBezierTo(8.75, 22, 8.55, 21.863)
      ..quadraticBezierTo(8.35, 21.725, 8.275, 21.475)
      ..lineTo(5.7, 12.75)
      ..lineTo(2, 12.75)
      ..lineTo(2, 11.25)
      ..lineTo(6.25, 11.25)
      ..quadraticBezierTo(6.5, 11.25, 6.7, 11.387)
      ..quadraticBezierTo(6.9, 11.525, 6.975, 11.775)
      ..lineTo(8.875, 18.175)
      ..lineTo(12.275, 2.6)
      ..quadraticBezierTo(12.325, 2.325, 12.525, 2.163)
      ..quadraticBezierTo(12.725, 2, 13, 2)
      ..quadraticBezierTo(13.275, 2, 13.475, 2.15)
      ..quadraticBezierTo(13.675, 2.3, 13.725, 2.575)
      ..lineTo(16.075, 13.15)
      ..lineTo(17.775, 7.525)
      ..quadraticBezierTo(17.85, 7.275, 18.05, 7.138)
      ..quadraticBezierTo(18.25, 7, 18.5, 7)
      ..quadraticBezierTo(18.75, 7, 18.938, 7.125)
      ..quadraticBezierTo(19.125, 7.25, 19.2, 7.475)
      ..lineTo(20.55, 11.25)
      ..lineTo(22, 11.25)
      ..lineTo(22, 12.75)
      ..lineTo(20, 12.75)
      ..quadraticBezierTo(19.75, 12.75, 19.562, 12.613)
      ..quadraticBezierTo(19.375, 12.475, 19.3, 12.25)
      ..lineTo(18.55, 10.175)
      ..lineTo(16.7, 16.475)
      ..quadraticBezierTo(16.625, 16.725, 16.425, 16.875)
      ..quadraticBezierTo(16.225, 17.025, 15.975, 17)
      ..quadraticBezierTo(15.725, 16.975, 15.525, 16.825)
      ..quadraticBezierTo(15.325, 16.675, 15.275, 16.425)
      ..lineTo(13, 6.375)
      ..lineTo(9.725, 21.425)
      ..quadraticBezierTo(9.675, 21.675, 9.475, 21.825)
      ..quadraticBezierTo(9.275, 21.975, 9, 22)
      ..close();
    canvas.drawPath(path, Paint()..color = color);
  }

  @override
  bool shouldRepaint(_QuakePainter old) => old.color != color;
}

/// How fast a hazard arrives, in words someone can act on.
const kOnsetLabels = <String, String>{
  'instant': 'No warning possible',
  'minutes': 'Minutes',
  'hours': 'Hours',
  'days': 'Days',
  'seasons': 'Weeks to months',
};

/// The overall level as an answer rather than a label.
const kRiskWords = <String, String>{
  'LOW': 'All clear for now',
  'MODERATE': 'Stay alert',
  'HIGH': 'Take action',
  'EXTREME': 'Act now — danger',
};
