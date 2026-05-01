// lib/screens/curator_screen.dart
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../models/models.dart';
import '../theme/app_theme.dart';
import '../widgets/shared_widgets.dart';

class CuratorScreen extends StatefulWidget {
  const CuratorScreen({super.key});

  @override
  State<CuratorScreen> createState() => _CuratorScreenState();
}

class _CuratorScreenState extends State<CuratorScreen> {
  final _ctrl = TextEditingController();
  final _scroll = ScrollController();

  @override
  void dispose() {
    _ctrl.dispose();
    _scroll.dispose();
    super.dispose();
  }

  void _send(AppState state) {
    final text = _ctrl.text.trim();
    if (text.isEmpty) return;
    _ctrl.clear();
    state.addChatMessage(text);
    Future.delayed(const Duration(milliseconds: 300), () {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final msgs = state.chatMessages;

    return Scaffold(
      backgroundColor: AlexandriaTheme.background,
      appBar: const AlexandriaAppBar(),
      body: Column(
        children: [
          // ── Messages ──────────────────────────────────────────────────
          Expanded(
            child: ListView.builder(
              controller: _scroll,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              itemCount: msgs.length + 1, // +1 for date chip at top
              itemBuilder: (_, i) {
                if (i == 0) return _DateChip(date: DateTime.now());
                final msg = msgs[i - 1];
                return _MessageBubble(message: msg);
              },
            ),
          ),

          // ── Quick actions row ──────────────────────────────────────────
          if (msgs.isNotEmpty && msgs.last.quickActions.isNotEmpty)
            _QuickActionsRow(actions: msgs.last.quickActions),

          // ── Input bar ─────────────────────────────────────────────────
          _InputBar(
            controller: _ctrl,
            onSend: () => _send(state),
          ),
        ],
      ),
    );
  }
}

// ── Date chip ─────────────────────────────────────────────────────────────────

class _DateChip extends StatelessWidget {
  final DateTime date;
  const _DateChip({required this.date});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Container(
        margin: const EdgeInsets.only(bottom: 20),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        decoration: BoxDecoration(
          color: AlexandriaTheme.border,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(
          'TODAY — ${DateFormat('MMM d').format(date).toUpperCase()}',
          style: GoogleFonts.inter(
            fontSize: 11,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.8,
            color: AlexandriaTheme.subtle,
          ),
        ),
      ),
    );
  }
}

// ── Message bubble ────────────────────────────────────────────────────────────

class _MessageBubble extends StatelessWidget {
  final ChatMessage message;
  const _MessageBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    if (message.isUser) return _UserBubble(message: message);
    return _AiBubble(message: message);
  }
}

class _UserBubble extends StatelessWidget {
  final ChatMessage message;
  const _UserBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerRight,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Container(
            margin: const EdgeInsets.only(bottom: 4, left: 60),
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
            decoration: BoxDecoration(
              color: AlexandriaTheme.primary,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(18),
                topRight: Radius.circular(18),
                bottomLeft: Radius.circular(18),
                bottomRight: Radius.circular(4),
              ),
            ),
            child: Text(
              message.text,
              style: GoogleFonts.inter(
                fontSize: 15,
                color: Colors.white,
                height: 1.4,
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: Text(
              DateFormat('h:mm a').format(message.time),
              style: GoogleFonts.inter(fontSize: 11, color: AlexandriaTheme.subtle),
            ),
          ),
        ],
      ),
    );
  }
}

class _AiBubble extends StatelessWidget {
  final ChatMessage message;
  const _AiBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // AI avatar
          Container(
            width: 38, height: 38,
            margin: const EdgeInsets.only(right: 10, top: 2),
            decoration: BoxDecoration(
              color: AlexandriaTheme.accent,
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Center(
              child: SparkleIcon(size: 18, color: Colors.white),
            ),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  margin: const EdgeInsets.only(bottom: 8, right: 40),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AlexandriaTheme.surface,
                    borderRadius: const BorderRadius.only(
                      topLeft: Radius.circular(4),
                      topRight: Radius.circular(18),
                      bottomLeft: Radius.circular(18),
                      bottomRight: Radius.circular(18),
                    ),
                    border: Border.all(color: AlexandriaTheme.border),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // AI text — bold + italic with blue highlight for key terms
                      _RichAiText(text: message.text),

                      // Reminder card
                      if (message.reminder != null) ...[
                        const Divider(height: 18),
                        _ReminderCardWidget(reminder: message.reminder!),
                      ],
                    ],
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.only(bottom: 16, left: 2),
                  child: Text(
                    'JUST NOW',
                    style: GoogleFonts.inter(
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.8,
                      color: AlexandriaTheme.subtle,
                    ),
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

class _RichAiText extends StatelessWidget {
  final String text;
  const _RichAiText({required this.text});

  @override
  Widget build(BuildContext context) {
    // Simple parser: highlight words in **...** or the main subject in blue
    return Text.rich(
      _parseSpans(text),
      style: GoogleFonts.playfairDisplay(
        fontSize: 16,
        fontStyle: FontStyle.italic,
        color: AlexandriaTheme.onSurface,
        height: 1.5,
      ),
    );
  }

  TextSpan _parseSpans(String text) {
    // Highlight text inside [] as blue + bold
    final spans = <InlineSpan>[];
    final regex = RegExp(r'\[([^\]]+)\]');
    int last = 0;
    for (final match in regex.allMatches(text)) {
      if (match.start > last) {
        spans.add(TextSpan(text: text.substring(last, match.start)));
      }
      spans.add(TextSpan(
        text: match.group(1),
        style: GoogleFonts.playfairDisplay(
          fontSize: 16,
          fontStyle: FontStyle.italic,
          fontWeight: FontWeight.w700,
          color: AlexandriaTheme.primary,
        ),
      ));
      last = match.end;
    }
    if (last < text.length) {
      spans.add(TextSpan(text: text.substring(last)));
    }
    return TextSpan(children: spans);
  }
}

class _ReminderCardWidget extends StatelessWidget {
  final ReminderCard reminder;
  const _ReminderCardWidget({required this.reminder});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AlexandriaTheme.background,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          Container(
            width: 36, height: 36,
            decoration: BoxDecoration(
              color: AlexandriaTheme.accentLight,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.calendar_month_outlined, size: 18, color: AlexandriaTheme.accent),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  reminder.label,
                  style: GoogleFonts.inter(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1,
                    color: AlexandriaTheme.accent,
                  ),
                ),
                Text(
                  reminder.detail,
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                    color: AlexandriaTheme.onSurface,
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

// ── Quick actions ─────────────────────────────────────────────────────────────

class _QuickActionsRow extends StatelessWidget {
  final List<QuickAction> actions;
  const _QuickActionsRow({required this.actions});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AlexandriaTheme.background,
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: actions.map((a) => _QuickActionChip(action: a)).toList(),
        ),
      ),
    );
  }
}

class _QuickActionChip extends StatelessWidget {
  final QuickAction action;
  const _QuickActionChip({required this.action});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(right: 10),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      width: 160,
      decoration: BoxDecoration(
        color: AlexandriaTheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AlexandriaTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(action.icon, style: const TextStyle(fontSize: 18)),
          const SizedBox(height: 6),
          Text(
            action.label,
            style: GoogleFonts.inter(
              fontSize: 13,
              fontWeight: FontWeight.w500,
              color: AlexandriaTheme.onSurface,
            ),
          ),
        ],
      ),
    );
  }
}

// ── Input bar ─────────────────────────────────────────────────────────────────

class _InputBar extends StatelessWidget {
  final TextEditingController controller;
  final VoidCallback onSend;
  const _InputBar({required this.controller, required this.onSend});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.fromLTRB(
        12, 10, 12, MediaQuery.of(context).viewInsets.bottom + 14,
      ),
      decoration: const BoxDecoration(
        color: AlexandriaTheme.surface,
        border: Border(top: BorderSide(color: AlexandriaTheme.border)),
      ),
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.attach_file, color: AlexandriaTheme.subtle),
            onPressed: () {},
          ),
          Expanded(
            child: TextField(
              controller: controller,
              onSubmitted: (_) => onSend(),
              decoration: InputDecoration(
                hintText: 'Note down a thought...',
                hintStyle: GoogleFonts.inter(
                  fontSize: 14,
                  color: AlexandriaTheme.subtle,
                ),
                filled: true,
                fillColor: AlexandriaTheme.background,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
                contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              ),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            icon: const Icon(Icons.mic_none, color: AlexandriaTheme.primary),
            onPressed: () {},
          ),
          GestureDetector(
            onTap: onSend,
            child: Container(
              width: 44, height: 44,
              decoration: BoxDecoration(
                color: AlexandriaTheme.primary,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(Icons.arrow_upward, color: Colors.white, size: 20),
            ),
          ),
        ],
      ),
    );
  }
}
