// lib/widgets/shared_widgets.dart
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';

// ── App bar ───────────────────────────────────────────────────────────────────

class AlexandriaAppBar extends StatelessWidget implements PreferredSizeWidget {
  final String? subtitle;
  final List<Widget>? actions;

  const AlexandriaAppBar({super.key, this.subtitle, this.actions});

  @override
  Size get preferredSize => const Size.fromHeight(56);

  @override
  Widget build(BuildContext context) {
    return AppBar(
      leading: IconButton(
        icon: const Icon(Icons.menu, size: 22),
        onPressed: () {},
      ),
      title: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'ALEXANDRIA',
            style: GoogleFonts.playfairDisplay(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              letterSpacing: 3,
              color: AlexandriaTheme.onSurface,
            ),
          ),
          if (subtitle != null) ...[
            const SizedBox(width: 8),
            Text(
              subtitle!,
              style: GoogleFonts.inter(
                fontSize: 10,
                fontWeight: FontWeight.w500,
                letterSpacing: 0.5,
                color: AlexandriaTheme.subtle,
              ),
            ),
          ],
        ],
      ),
      centerTitle: true,
      actions: actions ??
          [
            Padding(
              padding: const EdgeInsets.only(right: 16),
              child: CircleAvatar(
                radius: 18,
                backgroundColor: const Color(0xFFE8D5C0),
                child: const Icon(Icons.person, size: 18, color: Color(0xFF8B6040)),
              ),
            ),
          ],
    );
  }
}

// ── Section label ─────────────────────────────────────────────────────────────

class SectionLabel extends StatelessWidget {
  final String text;
  final IconData? icon;
  final Color? iconColor;

  const SectionLabel(this.text, {super.key, this.icon, this.iconColor});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        if (icon != null) ...[
          Icon(icon, size: 13, color: iconColor ?? AlexandriaTheme.subtle),
          const SizedBox(width: 5),
        ],
        Text(
          text,
          style: GoogleFonts.inter(
            fontSize: 11,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.2,
            color: iconColor ?? AlexandriaTheme.subtle,
          ),
        ),
      ],
    );
  }
}

// ── Week day strip ────────────────────────────────────────────────────────────

class WeekDayStrip extends StatelessWidget {
  final DateTime selectedDay;
  final void Function(DateTime) onDaySelected;

  const WeekDayStrip({
    super.key,
    required this.selectedDay,
    required this.onDaySelected,
  });

  @override
  Widget build(BuildContext context) {
    final today = DateTime.now();
    // Show a 7-day window centered on selected
    final start = selectedDay.subtract(const Duration(days: 3));
    final days = List.generate(7, (i) => start.add(Duration(days: i)));

    return SizedBox(
      height: 76,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: days.map((day) {
          final isSelected = _same(day, selectedDay);
          final isToday = _same(day, today);

          return GestureDetector(
            onTap: () => onDaySelected(day),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 44,
              height: 68,
              decoration: BoxDecoration(
                color: isSelected ? AlexandriaTheme.primary : Colors.transparent,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    _weekday(day),
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: isSelected
                          ? Colors.white.withOpacity(0.75)
                          : AlexandriaTheme.subtle,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    '${day.day}',
                    style: GoogleFonts.playfairDisplay(
                      fontSize: 20,
                      fontWeight: FontWeight.w700,
                      color: isSelected
                          ? Colors.white
                          : isToday
                              ? AlexandriaTheme.primary
                              : AlexandriaTheme.onSurface,
                    ),
                  ),
                ],
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  bool _same(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  String _weekday(DateTime d) {
    const days = ['MON','TUE','WED','THU','FRI','SAT','SUN'];
    return days[d.weekday - 1];
  }
}

// ── Surface card ──────────────────────────────────────────────────────────────

class SurfaceCard extends StatelessWidget {
  final Widget child;
  final EdgeInsets? padding;
  final Color? color;
  final BorderRadius? borderRadius;
  final Border? border;

  const SurfaceCard({
    super.key,
    required this.child,
    this.padding,
    this.color,
    this.borderRadius,
    this.border,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding ?? const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color ?? AlexandriaTheme.surface,
        borderRadius: borderRadius ?? BorderRadius.circular(16),
        border: border ?? Border.all(color: AlexandriaTheme.border),
      ),
      child: child,
    );
  }
}

// ── Sparkle icon (AI indicator) ───────────────────────────────────────────────

class SparkleIcon extends StatelessWidget {
  final double size;
  final Color? color;

  const SparkleIcon({super.key, this.size = 18, this.color});

  @override
  Widget build(BuildContext context) {
    return Icon(
      Icons.auto_awesome,
      size: size,
      color: color ?? AlexandriaTheme.primary,
    );
  }
}
