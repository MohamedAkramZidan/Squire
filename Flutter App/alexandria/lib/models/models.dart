// lib/models/models.dart
import 'package:flutter/material.dart';

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

// Shared state / mock data

class AppState extends ChangeNotifier {
  DateTime selectedDay = DateTime.now();
  int navIndex = 0; // calendar tab active by default

  // ── Calendar events ──────────────────────────────────────────────────────────
  late List<CalendarEvent> events;

  // ── Deadlines ─────────────────────────────────────────────────────────────────
  final List<Deadline> deadlines = [
    Deadline(
      title: 'Manuscript Final Review',
      section: 'Section: Theoretical Physics Anthology',
      dueLabel: 'Today, 5:00 PM',
      isToday: true,
      priority: Priority.high,
      category: 'HIGH PRIORITY',
    ),
    Deadline(
      title: 'Grant Application Submission',
      section: 'Digital Humanities Fund',
      dueLabel: 'Oct 26',
      priority: Priority.medium,
      category: 'INSTITUTIONAL',
    ),
    Deadline(
      title: 'Archive Digitization Sync',
      section: 'Personal Records — Folder 14',
      dueLabel: 'Oct 29',
      priority: Priority.low,
      category: 'MAINTENANCE',
    ),
  ];

  // ── AI tasks ─────────────────────────────────────────────────────────────────
  final List<AiTask> researchTasks = [
    AiTask(label: 'Analyze 14th century cartography notes'),
    AiTask(label: 'Cross-reference bibliography with JSTOR'),
  ];

  final List<AiTask> curationTasks = [
    AiTask(label: 'Backup weekly manuscript drafts', completed: true),
    AiTask(label: 'Update membership for Library of Congress'),
  ];

  // ── Meetings ─────────────────────────────────────────────────────────────────
  late List<Meeting> meetings;

  // ── Chat ─────────────────────────────────────────────────────────────────────
  List<ChatMessage> chatMessages = [
    ChatMessage(
      id: '1',
      text: 'I have a deadline to hand in Sheet 2 next Monday.',
      isUser: true,
      time: DateTime.now().subtract(const Duration(minutes: 5)),
    ),
    ChatMessage(
      id: '2',
      text:
          "Of course. I've recorded the deadline for Sheet 2 on Monday, October 30th.",
      isUser: false,
      time: DateTime.now(),
      reminder: ReminderCard(
        label: 'REMINDER SET',
        detail: 'Monday, 9:00 AM — Hand in Sheet 2',
      ),
      quickActions: [
        QuickAction(icon: '📜', label: 'Review research for Sheet 2'),
        QuickAction(icon: '✅', label: 'Add sub-tasks'),
      ],
    ),
  ];

  AppState() {
    final now = DateTime.now();
    events = [
      CalendarEvent(
        id: '1',
        title: 'Editorial Board Review',
        description:
            'Quarterly review of upcoming manuscripts and archival digitization priorities for the winter release.',
        date: now,
        startTime: const TimeOfDay(hour: 9, minute: 30),
        endTime: const TimeOfDay(hour: 10, minute: 45),
        type: EventType.meeting,
        location: 'LIBRARY WING B',
        attendees: ['A', 'B', '+4'],
      ),
      CalendarEvent(
        id: '2',
        title: 'Manuscript: The Golden Bough (V3)',
        date: now,
        type: EventType.deadline,
        priority: Priority.high,
        dueLabel: '12:00 PM',
        isAllDay: false,
      ),
      CalendarEvent(
        id: '3',
        title: 'Deep Work: Comparative Mythology',
        date: now,
        startTime: const TimeOfDay(hour: 14, minute: 0),
        endTime: const TimeOfDay(hour: 16, minute: 30),
        type: EventType.research,
      ),
      CalendarEvent(
        id: '4',
        title: 'Philosophical Inquiry',
        date: now.add(const Duration(days: 1)),
        startTime: const TimeOfDay(hour: 14, minute: 0),
        type: EventType.meeting,
        location: 'Virtual Hall',
      ),
      CalendarEvent(
        id: '5',
        title: 'Team Sync',
        date: now.add(const Duration(days: 3)),
        startTime: const TimeOfDay(hour: 10, minute: 0),
        type: EventType.meeting,
      ),
    ];

    meetings = [
      Meeting(
        date: now.add(const Duration(days: 1)),
        title: 'Philosophical Inquiry',
        time: '14:00',
        location: 'Virtual Hall',
      ),
      Meeting(
        date: now.add(const Duration(days: 2)),
        title: 'Metadata Standards Review',
        time: '10:30',
        location: 'Faculty Lounge',
      ),
    ];
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

  void addChatMessage(String text) {
    chatMessages.add(ChatMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      text: text,
      isUser: true,
      time: DateTime.now(),
    ));
    notifyListeners();
    // Simulate AI response
    Future.delayed(const Duration(milliseconds: 800), () {
      chatMessages.add(ChatMessage(
        id: '${DateTime.now().millisecondsSinceEpoch}r',
        text:
            "I've noted that. I'll update your schedule and set a reminder accordingly.",
        isUser: false,
        time: DateTime.now(),
      ));
      notifyListeners();
    });
  }
}
