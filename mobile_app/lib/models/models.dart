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

  late List<CalendarEvent> events;

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

  final List<AiTask> researchTasks = [
    AiTask(label: 'Analyze 14th century cartography notes'),
    AiTask(label: 'Cross-reference bibliography with JSTOR'),
  ];

  final List<AiTask> curationTasks = [
    AiTask(label: 'Backup weekly manuscript drafts', completed: true),
    AiTask(label: 'Update membership for Library of Congress'),
  ];

  late List<Meeting> meetings;

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
      final data = await SquireApi.predict(text);

      final result = data['result'] as Map<String, dynamic>;
      final decision = data['decision'] as Map<String, dynamic>;

      final action = result['action'] as String? ?? 'unknown';
      final obj = result['object'] as String? ?? 'unknown';
      final entities = result['entities'] as List<dynamic>? ?? [];

      // 4. Build human-readable reply
      final decisionType = decision['decision'] as String? ?? 'EXECUTE';
      final replyText = _buildReply(action, obj, entities, decisionType, decision);

      // 5. Build reminder card — only for ADD MEETING or ADD TASK
      ReminderCard? reminder;
      if (action == 'ADD' && decisionType == 'EXECUTE') {
        final dateEntity = entities.firstWhere(
          (e) => e['type'] == 'DATE' || e['type'] == 'TIME',
          orElse: () => null,
        );
        reminder = ReminderCard(
          label: obj == 'MEETING' ? 'MEETING ADDED' : 'TASK ADDED',
          detail: dateEntity != null
              ? '$obj — ${dateEntity['value']}'
              : 'Added to your schedule',
        );
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

  /// Converts NLU output into a readable AI reply sentence.
  String _buildReply(
    String action,
    String obj,
    List<dynamic> entities,
    String decisionType,
    Map<String, dynamic> decision,
  ) {
    // If backend is not confident — ask user to rephrase
    if (decisionType == 'REJECT') {
      return "I didn't quite understand that. Could you rephrase?";
    }

    // If backend needs more info — show its clarifying questions
    if (decisionType == 'CLARIFY') {
      final questions = decision['questions'] as List<dynamic>? ?? [];
      final q = questions.isNotEmpty ? questions.first as String : 'Could you give me more details?';
      return q;
    }

    // Extract useful entities
    final dateEntity = entities.firstWhere(
      (e) => e['type'] == 'DATE' || e['type'] == 'TIME',
      orElse: () => null,
    );
    final titleEntity = entities.firstWhere(
      (e) => e['type'] == 'TITLE',
      orElse: () => null,
    );
    final personEntity = entities.firstWhere(
      (e) => e['type'] == 'PERSON',
      orElse: () => null,
    );

    final timeStr    = dateEntity?['value']  as String? ?? '';
    final title      = titleEntity?['value'] as String? ?? '';
    final person     = personEntity?['value'] as String? ?? '';

    // action = ADD | GET | UPDATE | DELETE
    // obj    = TASK | MEETING | PROGRESS | NOTE
    switch ('$action:$obj') {
      case 'ADD:TASK':
        return timeStr.isNotEmpty
            ? "I've added the task [${title.isNotEmpty ? title : 'new task'}] due [$timeStr]."
            : "I've added [${title.isNotEmpty ? title : 'new task'}] to your tasks.";

      case 'ADD:MEETING':
        return timeStr.isNotEmpty
            ? "I've scheduled a [MEETING]${person.isNotEmpty ? ' with [$person]' : ''} on [$timeStr]."
            : "I've added a [MEETING]${person.isNotEmpty ? ' with [$person]' : ''} to your calendar.";

      case 'ADD:NOTE':
        return "I've saved your [NOTE]${title.isNotEmpty ? ': [$title]' : ''}.";

      case 'ADD:PROGRESS':
        return "I've logged your [PROGRESS] update.";

      case 'GET:TASK':
        return timeStr.isNotEmpty
            ? "Here are your [TASKS] for [$timeStr]."
            : "Here are your [TASKS].";

      case 'GET:MEETING':
        return timeStr.isNotEmpty
            ? "Here are your [MEETINGS] for [$timeStr]."
            : "Here are your upcoming [MEETINGS].";

      case 'GET:NOTE':
        return "Here are your [NOTES]${title.isNotEmpty ? ' about [$title]' : ''}.";

      case 'GET:PROGRESS':
        return "Here is your [PROGRESS] summary.";

      case 'UPDATE:TASK':
        return "I've updated the [TASK]${title.isNotEmpty ? ' [$title]' : ''}.";

      case 'UPDATE:MEETING':
        return "I've updated your [MEETING]${timeStr.isNotEmpty ? ' to [$timeStr]' : ''}.";

      case 'UPDATE:NOTE':
        return "I've updated your [NOTE].";

      case 'UPDATE:PROGRESS':
        return "I've updated your [PROGRESS].";

      case 'DELETE:TASK':
        return "I've removed the [TASK]${title.isNotEmpty ? ' [$title]' : ''}.";

      case 'DELETE:MEETING':
        return "I've cancelled the [MEETING]${timeStr.isNotEmpty ? ' on [$timeStr]' : ''}.";

      case 'DELETE:NOTE':
        return "I've deleted your [NOTE].";

      case 'DELETE:PROGRESS':
        return "I've cleared that [PROGRESS] entry.";

      default:
        return "Got it. I've processed your [$obj] request.";
    }
  }
}
