// lib/models/models.dart
// UPDATED: addChatMessage now calls the real Squire backend
import 'package:flutter/material.dart';
import 'package:alexandria/services/squire_api.dart';

enum EventType { meeting, deadline, research, task }

enum Priority { high, medium, low }

class CalendarEvent {
  final String id;
  final String title;
  final String? description;
  final DateTime date;
  final TimeOfDay? startTime;
  final TimeOfDay? endTime;
  final EventType type;
  final String? location;
  final List<String> attendees;
  final Priority priority;
  final bool isAllDay;
  final String? dueLabel;

  CalendarEvent({
    required this.id,
    required this.title,
    this.description,
    required this.date,
    this.startTime,
    this.endTime,
    this.type = EventType.task,
    this.location,
    this.attendees = const [],
    this.priority = Priority.medium,
    this.isAllDay = false,
    this.dueLabel,
  });
}

class ChatMessage {
  final String id;
  final String text;
  final bool isUser;
  final DateTime time;
  final ReminderCard? reminder;
  final List<QuickAction> quickActions;

  ChatMessage({
    required this.id,
    required this.text,
    required this.isUser,
    required this.time,
    this.reminder,
    this.quickActions = const [],
  });
}

class ReminderCard {
  final String label;
  final String detail;
  ReminderCard({required this.label, required this.detail});
}

class QuickAction {
  final String icon;
  final String label;
  QuickAction({required this.icon, required this.label});
}

class Deadline {
  final String title;
  final String? section;
  final String dueLabel;
  final bool isToday;
  final Priority priority;
  final String category;

  Deadline({
    required this.title,
    this.section,
    required this.dueLabel,
    this.isToday = false,
    this.priority = Priority.medium,
    required this.category,
  });
}

class AiTask {
  final String label;
  bool completed;
  AiTask({required this.label, this.completed = false});
}

class Meeting {
  final DateTime date;
  final String title;
  final String time;
  final String location;
  Meeting(
      {required this.date,
      required this.title,
      required this.time,
      required this.location});
}

// ── Shared state ────────────────────────────────────────────────────────────────

class AppState extends ChangeNotifier {
  DateTime selectedDay = DateTime.now();
  int navIndex = 0;

  /// The current user's ID — used for all backend calls.
  /// Change this to the actual logged-in user's ID once auth is wired up.
  int userId = 1;

  List<CalendarEvent> events = [];
  List<Deadline> deadlines = [];
  List<AiTask> researchTasks = [];
  List<AiTask> curationTasks = [];
  List<Meeting> meetings = [];
  List<ChatMessage> chatMessages = [];
  bool isLoading = true;

  AppState() {
    fetchInitialData();
  }

  Future<void> fetchInitialData() async {
    isLoading = true;
    notifyListeners();

    try {
      final tasksData = await SquireApi.getTasks(userId);
      final meetingsData = await SquireApi.getMeetings(userId);
      
      events = [];
      researchTasks = [];
      
      for (final t in tasksData) {
        final id = t['id'].toString();
        final title = t['title'] as String? ?? 'Untitled';
        final tDate = t['task_date'] as String?;
        final tTime = t['task_time'] as String?;
        final status = t['status'] as String? ?? 'pending';
        
        if (tDate != null) {
          final dateObj = DateTime.tryParse(tDate) ?? DateTime.now();
          TimeOfDay? start;
          if (tTime != null) {
            final parts = tTime.split(':');
            if (parts.length >= 2) {
              start = TimeOfDay(hour: int.parse(parts[0]), minute: int.parse(parts[1]));
            }
          }
          events.add(CalendarEvent(
            id: id,
            title: title,
            date: dateObj,
            startTime: start,
            type: EventType.task,
          ));
        } else {
          researchTasks.add(AiTask(label: title, completed: status == 'completed'));
        }
      }

      meetings = [];
      for (final m in meetingsData) {
        final id = m['id'].toString();
        final title = m['title'] as String? ?? 'Untitled';
        final mDate = m['meeting_date'] as String?;
        final mTime = m['meeting_time'] as String?;
        final location = m['location'] as String? ?? '';
        final person = m['person'] as String? ?? '';
        
        final dateObj = mDate != null ? (DateTime.tryParse(mDate) ?? DateTime.now()) : DateTime.now();
        TimeOfDay? start;
        String timeStr = 'TBD';
        if (mTime != null) {
          final parts = mTime.split(':');
          if (parts.length >= 2) {
            start = TimeOfDay(hour: int.parse(parts[0]), minute: int.parse(parts[1]));
            timeStr = mTime.substring(0, 5);
          }
        }
        
        meetings.add(Meeting(
          date: dateObj,
          title: title,
          time: timeStr,
          location: location.isEmpty && person.isNotEmpty ? 'With $person' : location,
        ));
        
        events.add(CalendarEvent(
          id: id,
          title: title,
          date: dateObj,
          startTime: start,
          type: EventType.meeting,
          location: location.isEmpty && person.isNotEmpty ? 'With $person' : location,
        ));
      }

      deadlines = []; 
      curationTasks = [];

      if (chatMessages.isEmpty) {
        chatMessages = [
          ChatMessage(
            id: 'welcome',
            text: 'Hello! I am connected to the backend. How can I help you?',
            isUser: false,
            time: DateTime.now(),
          )
        ];
      }

    } catch (e) {
      print('Error fetching data: $e');
    }

    isLoading = false;
    notifyListeners();
  }

  void setSelectedDay(DateTime day) {
    selectedDay = day;
    notifyListeners();
  }

  void setNavIndex(int i) {
    navIndex = i;
    notifyListeners();
  }

  List<CalendarEvent> eventsForDay(DateTime day) {
    return events
        .where((e) =>
            e.date.year == day.year &&
            e.date.month == day.month &&
            e.date.day == day.day)
        .toList();
  }

  void toggleAiTask(AiTask task) {
    task.completed = !task.completed;
    notifyListeners();
  }

  // ── UPDATED: calls real backend ─────────────────────────────────────────────

  Future<void> addChatMessage(String text) async {
    // 1. Add user message immediately
    chatMessages.add(ChatMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      text: text,
      isUser: true,
      time: DateTime.now(),
    ));
    notifyListeners();

    // 2. Show thinking placeholder
    final thinkingId = '${DateTime.now().millisecondsSinceEpoch}_thinking';
    chatMessages.add(ChatMessage(
      id: thinkingId,
      text: 'Thinking...',
      isUser: false,
      time: DateTime.now(),
    ));
    notifyListeners();

    try {
      // 3. Call the real backend
      final data = await SquireApi.predict(text, userId: userId);

      // Get the natural language response generated by the Response Layer
      final replyText = data['response'] as String? ?? 'I processed your request.';

      final result = data['result'] as Map<String, dynamic>?;
      final execution = data['execution'] as Map<String, dynamic>?;
      
      ReminderCard? reminder;
      if (execution != null && execution['status'] == 'EXECUTED') {
        if (result != null && result['action'] == 'ADD') {
          final obj = result['object'] as String? ?? 'ITEM';
          reminder = ReminderCard(
            label: '$obj ADDED',
            detail: 'Added to your schedule',
          );
        }
        // Auto-refresh the UI data in the background
        fetchInitialData();
      }

      // 6. Replace thinking with real reply
      chatMessages.removeWhere((m) => m.id == thinkingId);
      chatMessages.add(ChatMessage(
        id: '${DateTime.now().millisecondsSinceEpoch}r',
        text: replyText,
        isUser: false,
        time: DateTime.now(),
        reminder: reminder,
      ));
    } catch (e) {
      // 7. Show friendly error on failure
      chatMessages.removeWhere((m) => m.id == thinkingId);
      chatMessages.add(ChatMessage(
        id: '${DateTime.now().millisecondsSinceEpoch}err',
        text:
            'Sorry, I could not reach the server. Make sure the backend is running on port 8000.',
        isUser: false,
        time: DateTime.now(),
      ));
    }

    notifyListeners();
  }
}
