// lib/screens/dashboard_screen.dart
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../models/models.dart';
import '../theme/app_theme.dart';
import '../widgets/shared_widgets.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();

    return Scaffold(
      backgroundColor: AlexandriaTheme.background,
      appBar: const AlexandriaAppBar(),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
        children: [
          // ── Header ─────────────────────────────────────────────────────
          Text(
            "TODAY'S LEDGER — ${DateFormat('MMM d').format(DateTime.now()).toUpperCase()}",
            style: GoogleFonts.inter(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.3,
              color: AlexandriaTheme.subtle,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Curated Schedule',
            style: GoogleFonts.playfairDisplay(
              fontSize: 28,
              fontWeight: FontWeight.w700,
              color: AlexandriaTheme.onSurface,
            ),
          ),
          const SizedBox(height: 20),

          // ── Upcoming Deadlines ─────────────────────────────────────────
          _DeadlinesCard(deadlines: state.deadlines),
          const SizedBox(height: 16),

          // ── AI Research ────────────────────────────────────────────────
          _AiTaskCard(
            label: 'AI INTELLIGENCE',
            title: 'Deep Research',
            tasks: state.researchTasks,
            onToggle: state.toggleAiTask,
          ),
          const SizedBox(height: 16),

          // ── Curation Flow ──────────────────────────────────────────────
          _AiTaskCard(
            label: 'ADMINISTRATIVE',
            title: 'Curation Flow',
            tasks: state.curationTasks,
            onToggle: state.toggleAiTask,
            labelColor: AlexandriaTheme.subtle,
            showSparkle: false,
          ),
          const SizedBox(height: 16),

          // ── Next Meetings ──────────────────────────────────────────────
          _MeetingsCard(meetings: state.meetings),
          const SizedBox(height: 16),

          // ── Curator Insight ────────────────────────────────────────────
          _CuratorInsightCard(),
        ],
      ),
    );
  }
}

// ── Deadlines card ────────────────────────────────────────────────────────────

class _DeadlinesCard extends StatelessWidget {
  final List<Deadline> deadlines;
  const _DeadlinesCard({required this.deadlines});

  @override
  Widget build(BuildContext context) {
    return SurfaceCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Upcoming\nDeadlines',
                style: GoogleFonts.playfairDisplay(
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                  color: AlexandriaTheme.onSurface,
                  height: 1.2,
                ),
              ),
              const Spacer(),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    '${deadlines.length} URGENT',
                    style: GoogleFonts.inter(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.8,
                      color: AlexandriaTheme.danger,
                    ),
                  ),
                  Text(
                    'ENTRIES',
                    style: GoogleFonts.inter(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.8,
                      color: AlexandriaTheme.subtle,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),
          ...deadlines.map((d) => _DeadlineRow(deadline: d)),
        ],
      ),
    );
  }
}

class _DeadlineRow extends StatelessWidget {
  final Deadline deadline;
  const _DeadlineRow({required this.deadline});

  @override
  Widget build(BuildContext context) {
    final dotColor = deadline.priority == Priority.high
        ? AlexandriaTheme.danger
        : deadline.priority == Priority.medium
            ? AlexandriaTheme.accent
            : const Color(0xFFAAAAAA);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Container(
              width: 7, height: 7,
              decoration: BoxDecoration(color: dotColor, shape: BoxShape.circle),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  deadline.title,
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AlexandriaTheme.onSurface,
                  ),
                ),
                if (deadline.section != null)
                  Text(
                    deadline.section!,
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      fontStyle: FontStyle.italic,
                      color: AlexandriaTheme.subtle,
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                deadline.dueLabel,
                style: GoogleFonts.inter(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: deadline.isToday ? AlexandriaTheme.danger : AlexandriaTheme.onSurface,
                ),
              ),
              Text(
                deadline.category,
                style: GoogleFonts.inter(
                  fontSize: 9,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8,
                  color: AlexandriaTheme.subtle,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ── AI task card ──────────────────────────────────────────────────────────────

class _AiTaskCard extends StatelessWidget {
  final String label;
  final String title;
  final List<AiTask> tasks;
  final void Function(AiTask) onToggle;
  final Color? labelColor;
  final bool showSparkle;

  const _AiTaskCard({
    required this.label,
    required this.title,
    required this.tasks,
    required this.onToggle,
    this.labelColor,
    this.showSparkle = true,
  });

  @override
  Widget build(BuildContext context) {
    return SurfaceCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              if (showSparkle)
                const Padding(
                  padding: EdgeInsets.only(right: 5),
                  child: SparkleIcon(size: 13),
                ),
              Text(
                label,
                style: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.2,
                  color: showSparkle ? AlexandriaTheme.primary : (labelColor ?? AlexandriaTheme.subtle),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            title,
            style: GoogleFonts.playfairDisplay(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: AlexandriaTheme.onSurface,
            ),
          ),
          const SizedBox(height: 12),
          ...tasks.map((t) => _TaskRow(task: t, onToggle: () => onToggle(t))),
        ],
      ),
    );
  }
}

class _TaskRow extends StatelessWidget {
  final AiTask task;
  final VoidCallback onToggle;
  const _TaskRow({required this.task, required this.onToggle});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onToggle,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Row(
          children: [
            Container(
              width: 20, height: 20,
              decoration: BoxDecoration(
                color: task.completed ? AlexandriaTheme.primary : Colors.transparent,
                borderRadius: BorderRadius.circular(5),
                border: Border.all(
                  color: task.completed ? AlexandriaTheme.primary : AlexandriaTheme.border,
                  width: 1.5,
                ),
              ),
              child: task.completed
                  ? const Icon(Icons.check, size: 13, color: Colors.white)
                  : null,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                task.label,
                style: GoogleFonts.inter(
                  fontSize: 13,
                  color: task.completed ? AlexandriaTheme.subtle : AlexandriaTheme.onSurface,
                  decoration: task.completed ? TextDecoration.lineThrough : null,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Meetings card ─────────────────────────────────────────────────────────────

class _MeetingsCard extends StatelessWidget {
  final List<Meeting> meetings;
  const _MeetingsCard({required this.meetings});

  @override
  Widget build(BuildContext context) {
    return SurfaceCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        children: [
          Row(
            children: [
              Text(
                'Next Meetings',
                style: GoogleFonts.playfairDisplay(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                  color: AlexandriaTheme.onSurface,
                ),
              ),
              const Spacer(),
              const Icon(Icons.calendar_today_outlined, size: 18, color: AlexandriaTheme.primary),
            ],
          ),
          const SizedBox(height: 14),
          ...meetings.map((m) => _MeetingRow(meeting: m)),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () {},
              child: const Text('SCHEDULE NEW ENTRY'),
            ),
          ),
        ],
      ),
    );
  }
}

class _MeetingRow extends StatelessWidget {
  final Meeting meeting;
  const _MeetingRow({required this.meeting});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AlexandriaTheme.background,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Column(
            children: [
              Text(
                DateFormat('MMM').format(meeting.date).toUpperCase(),
                style: GoogleFonts.inter(
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8,
                  color: AlexandriaTheme.primary,
                ),
              ),
              Text(
                '${meeting.date.day}',
                style: GoogleFonts.playfairDisplay(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: AlexandriaTheme.onSurface,
                ),
              ),
            ],
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  meeting.title,
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AlexandriaTheme.onSurface,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  '${meeting.time} • ${meeting.location}',
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: AlexandriaTheme.subtle,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Curator insight card ──────────────────────────────────────────────────────

class _CuratorInsightCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AlexandriaTheme.accentLight,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE0CB80)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const SparkleIcon(size: 14, color: AlexandriaTheme.accent),
              const SizedBox(width: 5),
              Text(
                "CURATOR'S INSIGHT",
                style: GoogleFonts.inter(
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.2,
                  color: AlexandriaTheme.accent,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            '"Your output this week has shifted significantly toward archive management. Based on your upcoming deadlines, I recommend shifting 2 hours from \'Research\' to \'Drafting\' by Wednesday."',
            style: GoogleFonts.playfairDisplay(
              fontSize: 14,
              fontStyle: FontStyle.italic,
              color: const Color(0xFF444400),
              height: 1.6,
            ),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Text(
                'CONFIDENCE 94%',
                style: GoogleFonts.inter(
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8,
                  color: AlexandriaTheme.subtle,
                ),
              ),
              const Spacer(),
              Text(
                'ADJUST PLAN',
                style: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8,
                  color: AlexandriaTheme.primary,
                  decoration: TextDecoration.underline,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
