import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

/// Direct Groq API client for fast advisory generation.
///
/// Used as a fallback when the backend is unreachable, or for
/// instant advisory generation on the device.
///
/// The API key is injected at compile time via:
///   flutter run --dart-define=GROQ_API_KEY=gsk_...
///
/// This ensures the key never appears in source code.
class GroqService {
  static const _apiKey = String.fromEnvironment('GROQ_API_KEY');
  static const _model = String.fromEnvironment(
    'GROQ_MODEL',
    defaultValue: 'llama-3.3-70b-versatile',
  );
  static const _baseUrl = 'https://api.groq.com/openai/v1/chat/completions';

  final Dio _dio;

  /// Whether the Groq API is available (key was provided at compile time).
  static bool get isAvailable => _apiKey.isNotEmpty;

  GroqService()
      : _dio = Dio(BaseOptions(
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 15),
          headers: {
            'Authorization': 'Bearer $_apiKey',
            'Content-Type': 'application/json',
          },
        ));

  /// Generate an advisory directly via Groq API.
  ///
  /// Returns a Map with 'title', 'body', and 'actions' keys,
  /// or null if the call fails.
  Future<Map<String, dynamic>?> generateAdvisory({
    required String basinName,
    required String riverName,
    required String country,
    required String riskLevel,
    required double probability,
    required int populationAtRisk,
    required String role,
    required String language,
  }) async {
    if (!isAvailable) return null;

    final languageNames = {
      'en': 'English',
      'so': 'Somali',
      'sw': 'Swahili',
      'am': 'Amharic',
      'om': 'Oromo',
    };

    final roleDescriptions = {
      'farmer':
          'a small-scale farmer who grows crops and keeps livestock near the river',
      'pastoralist':
          'a pastoralist herder who moves livestock near the river',
      'county_officer':
          'a county/district disaster management officer',
      'community_leader': 'a village/community leader',
      'general': 'a resident living near the river floodplain',
    };

    final langName = languageNames[language] ?? 'English';
    final roleDesc = roleDescriptions[role] ?? roleDescriptions['general'];

    final prompt = '''You are Tayari, an AI flood early-warning system for East Africa. Generate a flood advisory.

CONTEXT:
- Location: $basinName, $riverName, $country
- Flood Risk Level: $riskLevel
- Flood Probability (next 3 days): ${(probability * 100).toStringAsFixed(0)}%
- Population at risk: ~$populationAtRisk

TARGET AUDIENCE:
- This advisory is for $roleDesc
- Write in $langName

INSTRUCTIONS:
1. Write a short TITLE (max 10 words). Match the tone to the risk level:
   LOW = calm reassurance, MODERATE = watchful, HIGH/EXTREME = urgent.
2. Write a BODY paragraph (3-5 sentences) in simple, clear language — no jargon,
   no panic. Reference the ${(probability * 100).toStringAsFixed(0)}% probability and be specific about timing.
   For LOW risk, reassure and give light preparedness steps — do NOT tell people to evacuate.
3. List 3-5 concrete ACTIONS the person can actually do, tailored to their role,
   ordered by what to do first. Keep each action to one short sentence.

Format your response EXACTLY as:
TITLE: [title]
BODY: [body paragraph]
ACTIONS:
- [action 1]
- [action 2]
- [action 3]

CRITICAL: Keep the labels "TITLE:", "BODY:", and "ACTIONS:" in English exactly as shown — they are parsing markers. Write only the CONTENT in $langName. Do not translate or omit the labels.''';

    try {
      final response = await _dio.post(_baseUrl, data: {
        'model': _model,
        'messages': [
          {'role': 'user', 'content': prompt}
        ],
        'max_tokens': 1024,
        'temperature': 0.7,
      });

      final text =
          response.data['choices'][0]['message']['content'] as String;
      return _parseAdvisoryResponse(text, riskLevel);
    } catch (e) {
      debugPrint('Groq advisory generation failed: $e');
      return null;
    }
  }

  /// Parse the structured LLM response into a map.
  Map<String, dynamic> _parseAdvisoryResponse(
      String text, String riskLevel) {
    String title = '';
    String body = '';
    final actions = <String>[];
    String? currentSection;

    for (final line in text.trim().split('\n')) {
      final trimmed = line.trim();
      if (trimmed.toUpperCase().startsWith('TITLE:')) {
        title = trimmed.substring(6).trim();
        currentSection = 'title';
      } else if (trimmed.toUpperCase().startsWith('BODY:')) {
        body = trimmed.substring(5).trim();
        currentSection = 'body';
      } else if (trimmed.toUpperCase().startsWith('ACTIONS:')) {
        currentSection = 'actions';
      } else if (currentSection == 'body' &&
          trimmed.isNotEmpty &&
          !trimmed.startsWith('-')) {
        body += ' $trimmed';
      } else if (currentSection == 'actions' && trimmed.startsWith('-')) {
        actions.add(trimmed.substring(1).trim());
      } else if (currentSection == 'actions' && trimmed.isNotEmpty) {
        actions.add(trimmed);
      }
    }

    if (title.isEmpty) title = 'Flood Warning \u2014 $riskLevel';
    if (body.isEmpty) {
      body = text.length > 500 ? text.substring(0, 500) : text;
    }
    if (actions.isEmpty) actions.add('Monitor official channels for updates');

    return {
      'title': title,
      'body': body.trim(),
      'actions': actions,
      'risk_level': riskLevel,
    };
  }
}
