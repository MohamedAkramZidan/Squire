// lib/services/squire_api.dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class SquireApi {
  // --- CHANGE THIS URL based on where you are running ---
  //
  // Android Emulator  → http://10.0.2.2:8000
  // iOS Simulator     → http://localhost:8000
  // Real phone        → http://<your-computer-LAN-ip>:8000
  //   (find with: ipconfig on Windows, ifconfig on Mac/Linux)
  //
  static const String _baseUrl = 'http://localhost:8000';

  /// Send text to the NLU backend and get a structured result back.
  static Future<Map<String, dynamic>> predict(String text) async {
    final uri = Uri.parse('$_baseUrl/predict');

    final response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'text': text}),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception(
          'Backend error ${response.statusCode}: ${response.body}');
    }
  }

  /// Quick health check — returns true if backend is running.
  static Future<bool> isHealthy() async {
    try {
      final uri = Uri.parse('$_baseUrl/health');
      final response = await http.get(uri);
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }
}
