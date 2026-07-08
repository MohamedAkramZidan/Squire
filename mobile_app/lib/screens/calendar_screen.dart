// lib/screens/calendar_screen.dart
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../models/models.dart';
import '../theme/app_theme.dart';
import '../widgets/shared_widgets.dart';

class CalendarScreen extends StatelessWidget {
  const CalendarScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final events = state.eventsForDay(state.selectedDay);

    return Scaffold(
      backgroundColor: AlexandriaTheme.background,
      appBar: const AlexandriaAppBar(),
      body: CustomScrollView(
        slivers: [
          // ── Header ──────────────────────────────────────────────────────
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'TIMELINE VIEW',
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.5,
                      color: AlexandriaTheme.accent,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    DateFormat('EEEE, MMM d').format(state.selectedDay),
                    style: GoogleFonts.playfairDisplay(
                      fontSize: 30,
                      fontWeight: FontWeight.w700,
                      color: AlexandriaTheme.onSurface,
                    ),
                  ),
                ],
              ),
            ),
          ),

          // ── Week strip ───────────────────────────────────────────────────
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
              child: WeekDayStrip(
                selectedDay: state.selectedDay,
                onDaySelected: state.setSelectedDay,
              ),
            ),
          ),

          // ── Event list ───────────────────────────────────────────────────
          if (events.isEmpty)
            SliverFillRemaining(
              child: _EmptyDay(onAdd: () => _showAddEvent(context, state)),
            )
          else
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 100),
              sliver: SliverList(
                delegate: SliverChildBuilderDelegate(
                  (_, i) {
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _buildEventCard(context, events[i]),
                    );
                  },
                  childCount: events.length,
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildEventCard(BuildContext context, CalendarEvent event) {
    switch (event.type) {
      case EventType.meeting:
        return _MeetingCard(event: event);
      case EventType.deadline:
        return _DeadlineCard(event: event);
      case EventType.research:
        return _ResearchCard(event: event);
      case EventType.task:
        return _TaskCard(event: event);
    }
  }

  void _showAddEvent(BuildContext context, AppState state) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => const _AddEventSheet(),
    );
  }
}

// ── Meeting Card ──────────────────────────────────────────────────────────────

class _MeetingCard extends StatelessWidget {
  final CalendarEvent event;
  const _MeetingCard({required this.event});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AlexandriaTheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AlexandriaTheme.border),
      ),
      child: IntrinsicHeight(
        child: Row(
          children: [
            // Left blue bar
            Container(
              width: 4,
              decoration: const BoxDecoration(
                color: AlexandriaTheme.primary,
                borderRadius: BorderRadius.only(
                  topLeft: Radius.circular(16),
                  bottomLeft: Radius.circular(16),
                ),
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SectionLabel(
                      'MEETING',
                      icon: Icons.people_outline,
                      iconColor: AlexandriaTheme.primary,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      event.title,
                      style: GoogleFonts.playfairDisplay(
                        fontSize: 19,
                        fontWeight: FontWeight.w700,
                        color: AlexandriaTheme.onSurface,
                      ),
                    ),
                    if (event.description != null) ...[
                      const SizedBox(height: 6),
                      Text(
                        event.description!,
                        style: GoogleFonts.inter(
                          fontSize: 13,
                          color: const Color(0xFF555577),
                          height: 1.5,
                        ),
                      ),
                    ],
                    if (event.attendees.isNotEmpty) ...[
                      const SizedBox(height: 10),
                      _AttendeeRow(attendees: event.attendees),
                    ],
                    const Divider(height: 20, color: AlexandriaTheme.border),
                    Row(
                      children: [
                        const Icon(Icons.access_time,
                            size: 13, color: AlexandriaTheme.subtle),
                        const SizedBox(width: 5),
                        Text(
                          '${_fmtTime(event.startTime)} — ${_fmtTime(event.endTime)}',
                          style: GoogleFonts.inter(
                              fontSize: 12, color: AlexandriaTheme.subtle),
                        ),
                        if (event.location != null) ...[
                          const SizedBox(width: 14),
                          const Icon(Icons.location_on_outlined,
                              size: 13, color: AlexandriaTheme.subtle),
                          const SizedBox(width: 4),
                          Text(
                            event.location!,
                            style: GoogleFonts.inter(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: AlexandriaTheme.subtle,
                              letterSpacing: 0.5,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _fmtTime(TimeOfDay? t) {
    if (t == null) return '';
    final h = t.hourOfPeriod == 0 ? 12 : t.hourOfPeriod;
    final m = t.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }
}

class _AttendeeRow extends StatelessWidget {
  final List<String> attendees;
  const _AttendeeRow({required this.attendees});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: List.generate(
        attendees.length > 3 ? 3 : attendees.length,
        (i) {
          final isLast = i == 2 && attendees.length > 3;
          return Transform.translate(
            offset: Offset(-i * 8.0, 0),
            child: CircleAvatar(
              radius: 14,
              backgroundColor:
                  isLast ? AlexandriaTheme.border : _avatarColor(i),
              child: isLast
                  ? Text(
                      '+${attendees.length - 2}',
                      style: GoogleFonts.inter(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: AlexandriaTheme.subtle,
                      ),
                    )
                  : Text(
                      attendees[i][0],
                      style: const TextStyle(fontSize: 11, color: Colors.white),
                    ),
            ),
          );
        },
      ),
    );
  }

  Color _avatarColor(int i) {
    const colors = [Color(0xFFB08060), Color(0xFF4A7A5A), Color(0xFF5A5A8A)];
    return colors[i % colors.length];
  }
}

// ── Task Card ─────────────────────────────────────────────────────────────────

class _TaskCard extends StatelessWidget {
  final CalendarEvent event;
  const _TaskCard({required this.event});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AlexandriaTheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AlexandriaTheme.border),
      ),
      child: IntrinsicHeight(
        child: Row(
          children: [
            // Left green bar to distinguish from meetings
            Container(
              width: 4,
              decoration: const BoxDecoration(
                color: Color(0xFF4A7A5A),
                borderRadius: BorderRadius.only(
                  topLeft: Radius.circular(16),
                  bottomLeft: Radius.circular(16),
                ),
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SectionLabel(
                      'TASK',
                      icon: Icons.assignment_outlined,
                      iconColor: const Color(0xFF4A7A5A),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      event.title,
                      style: GoogleFonts.playfairDisplay(
                        fontSize: 19,
                        fontWeight: FontWeight.w700,
                        color: AlexandriaTheme.onSurface,
                      ),
                    ),
                    if (event.description != null) ...[
                      const SizedBox(height: 6),
                      Text(
                        event.description!,
                        style: GoogleFonts.inter(
                          fontSize: 13,
                          color: const Color(0xFF555577),
                          height: 1.5,
                        ),
                      ),
                    ],
                    const Divider(height: 20, color: AlexandriaTheme.border),
                    Row(
                      children: [
                        if (event.startTime != null) ...[
                          const Icon(Icons.access_time,
                              size: 13, color: AlexandriaTheme.subtle),
                          const SizedBox(width: 5),
                          Text(
                            _fmtTime(event.startTime),
                            style: GoogleFonts.inter(
                                fontSize: 12, color: AlexandriaTheme.subtle),
                          ),
                        ],
                        if (event.dueLabel != null) ...[
                          const SizedBox(width: 14),
                          const Icon(Icons.flag_outlined,
                              size: 13, color: AlexandriaTheme.subtle),
                          const SizedBox(width: 4),
                          Text(
                            event.dueLabel!,
                            style: GoogleFonts.inter(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: AlexandriaTheme.subtle,
                              letterSpacing: 0.5,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _fmtTime(TimeOfDay? t) {
    if (t == null) return '';
    final h = t.hourOfPeriod == 0 ? 12 : t.hourOfPeriod;
    final m = t.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }
}

// ── Deadline Card ─────────────────────────────────────────────────────────────

class _DeadlineCard extends StatelessWidget {
  final CalendarEvent event;
  const _DeadlineCard({required this.event});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AlexandriaTheme.accentLight,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE8D890)),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: AlexandriaTheme.accent,
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Center(
              child: Text('!',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.w900)),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'FINAL DEADLINE',
                  style: GoogleFonts.inter(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.2,
                    color: AlexandriaTheme.accent,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  event.title,
                  style: GoogleFonts.playfairDisplay(
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                    color: AlexandriaTheme.onSurface,
                  ),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                'DUE BY',
                style: GoogleFonts.inter(
                  fontSize: 9,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1,
                  color: AlexandriaTheme.subtle,
                ),
              ),
              Text(
                event.dueLabel ?? '',
                style: GoogleFonts.playfairDisplay(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  fontStyle: FontStyle.italic,
                  color: AlexandriaTheme.onSurface,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ── Research Card ─────────────────────────────────────────────────────────────

class _ResearchCard extends StatelessWidget {
  final CalendarEvent event;
  const _ResearchCard({required this.event});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AlexandriaTheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AlexandriaTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SectionLabel('RESEARCH', icon: Icons.menu_book_outlined),
          const SizedBox(height: 8),
          Text(
            event.title,
            style: GoogleFonts.playfairDisplay(
              fontSize: 20,
              fontWeight: FontWeight.w700,
              color: AlexandriaTheme.onSurface,
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              _Chip(
                icon: Icons.folder_outlined,
                label: '3 FOLDERS',
                color: AlexandriaTheme.primary,
              ),
              const SizedBox(width: 8),
              _Chip(
                icon: Icons.star_outline,
                label: 'HIGH FOCUS',
                color: AlexandriaTheme.accent,
              ),
            ],
          ),
          const Divider(height: 18, color: AlexandriaTheme.border),
          Row(
            children: [
              const Icon(Icons.access_time,
                  size: 13, color: AlexandriaTheme.subtle),
              const SizedBox(width: 5),
              Text(
                '02:00 — 04:30',
                style: GoogleFonts.inter(
                    fontSize: 12, color: AlexandriaTheme.subtle),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  const _Chip({required this.icon, required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.25)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 4),
          Text(
            label,
            style: GoogleFonts.inter(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: color,
              letterSpacing: 0.5,
            ),
          ),
        ],
      ),
    );
  }
}

// ── Add slot card ────────────────────────────────────────────────────────s─────

class _AddSlotCard extends StatelessWidget {
  final VoidCallback onTap;
  const _AddSlotCard({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 54,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: AlexandriaTheme.border,
            style: BorderStyle.solid,
            width: 1.5,
          ),
        ),
        child: Center(
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.add, size: 16, color: AlexandriaTheme.subtle),
              const SizedBox(width: 6),
              Text(
                'SCHEDULE AFTERNOON SYNC',
                style: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.2,
                  color: AlexandriaTheme.subtle,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Empty day ─────────────────────────────────────────────────────────────────

class _EmptyDay extends StatelessWidget {
  final VoidCallback onAdd;
  const _EmptyDay({required this.onAdd});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Icon(Icons.calendar_today_outlined,
            size: 48, color: AlexandriaTheme.border),
        const SizedBox(height: 12),
        Text(
          'No entries for this day',
          style: GoogleFonts.playfairDisplay(
            fontSize: 18,
            color: AlexandriaTheme.subtle,
          ),
        ),
        const SizedBox(height: 16),
        TextButton.icon(
          onPressed: onAdd,
          icon: const Icon(Icons.add, size: 16),
          label: const Text('Schedule Entry'),
        ),
      ],
    );
  }
}

// ── Add event bottom sheet ────────────────────────────────────────────────────

class _AddEventSheet extends StatefulWidget {
  const _AddEventSheet();

  @override
  State<_AddEventSheet> createState() => _AddEventSheetState();
}

class _AddEventSheetState extends State<_AddEventSheet> {
  final _titleCtrl = TextEditingController();
  EventType _type = EventType.meeting;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
        20,
        20,
        20,
        MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: AlexandriaTheme.border,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 20),
          Text(
            'New Entry',
            style: GoogleFonts.playfairDisplay(
              fontSize: 22,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _titleCtrl,
            decoration: InputDecoration(
              hintText: 'Entry title',
              filled: true,
              fillColor: AlexandriaTheme.background,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide.none,
              ),
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            children: EventType.values.map((t) {
              final sel = t == _type;
              return ChoiceChip(
                label: Text(_typeLabel(t)),
                selected: sel,
                onSelected: (_) => setState(() => _type = t),
                selectedColor: AlexandriaTheme.primaryLight,
                labelStyle: TextStyle(
                  color: sel ? AlexandriaTheme.primary : AlexandriaTheme.subtle,
                  fontWeight: FontWeight.w600,
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('ADD ENTRY'),
            ),
          ),
        ],
      ),
    );
  }

  String _typeLabel(EventType t) {
    switch (t) {
      case EventType.meeting:
        return 'Meeting';
      case EventType.deadline:
        return 'Deadline';
      case EventType.research:
        return 'Research';
      case EventType.task:
        return 'Task';
    }
  }
}
