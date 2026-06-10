// lib/screens/library_screen.dart
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import '../widgets/shared_widgets.dart';

class LibraryScreen extends StatefulWidget {
  const LibraryScreen({super.key});

  @override
  State<LibraryScreen> createState() => _LibraryScreenState();
}

class _LibraryScreenState extends State<LibraryScreen> {
  final _titleCtrl = TextEditingController();
  final _bodyCtrl  = TextEditingController();
  bool _analyzing  = false;

  @override
  void dispose() {
    _titleCtrl.dispose();
    _bodyCtrl.dispose();
    super.dispose();
  }

  void _analyzeWithAi() async {
    if (_bodyCtrl.text.trim().isEmpty && _titleCtrl.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Write something first before analyzing.'),
          behavior: SnackBarBehavior.floating,
        ),
      );
      return;
    }
    setState(() => _analyzing = true);
    await Future.delayed(const Duration(seconds: 2));
    setState(() => _analyzing = false);
    _showInsightSheet();
  }

  void _showInsightSheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const _InsightSheet(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AlexandriaTheme.background,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.menu, size: 22, color: AlexandriaTheme.onSurface),
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
            const SizedBox(width: 10),
            Text(
              'DRAFT AUTO-SAVED',
              style: GoogleFonts.inter(
                fontSize: 9,
                fontWeight: FontWeight.w600,
                letterSpacing: 0.8,
                color: AlexandriaTheme.subtle,
              ),
            ),
          ],
        ),
        centerTitle: true,
        backgroundColor: AlexandriaTheme.background,
        elevation: 0,
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Container(
              width: 34, height: 34,
              decoration: BoxDecoration(
                color: const Color(0xFFE8D0B0),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.phone_iphone, size: 18, color: Color(0xFF8B5A20)),
            ),
          ),
        ],
      ),
      body: Stack(
        children: [
          // ── Main editor card ──────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 100),
            child: _ManuscriptEditor(
              titleCtrl: _titleCtrl,
              bodyCtrl: _bodyCtrl,
            ),
          ),

          // ── Analyze button pinned at bottom ───────────────────────────
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: Container(
              padding: const EdgeInsets.fromLTRB(40, 12, 40, 20),
              color: AlexandriaTheme.background,
              child: ElevatedButton.icon(
                onPressed: _analyzing ? null : _analyzeWithAi,
                icon: _analyzing
                    ? const SizedBox(
                        width: 18, height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white,
                        ),
                      )
                    : const SparkleIcon(size: 18, color: Colors.white),
                label: Text(
                  _analyzing ? 'ANALYZING...' : 'ANALYZE WITH AI',
                  style: GoogleFonts.inter(
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.2,
                    fontSize: 14,
                  ),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AlexandriaTheme.primary,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                  minimumSize: const Size(double.infinity, 52),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Manuscript editor ─────────────────────────────────────────────────────────

class _ManuscriptEditor extends StatelessWidget {
  final TextEditingController titleCtrl;
  final TextEditingController bodyCtrl;

  const _ManuscriptEditor({
    required this.titleCtrl,
    required this.bodyCtrl,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.06),
            blurRadius: 20,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Manuscript header bar ─────────────────────────────────────
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 18, 18, 0),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: AlexandriaTheme.accentLight,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFFDDC060)),
                    ),
                    child: Text(
                      'MANUSCRIPT',
                      style: GoogleFonts.inter(
                        fontSize: 10,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1.2,
                        color: const Color(0xFF8B7020),
                      ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Text(
                    'October 24th, 1924 • Room 402',
                    style: GoogleFonts.playfairDisplay(
                      fontSize: 13,
                      fontStyle: FontStyle.italic,
                      color: AlexandriaTheme.subtle,
                    ),
                  ),
                ],
              ),
            ),

            // ── Title field ───────────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 14, 18, 0),
              child: TextField(
                controller: titleCtrl,
                style: GoogleFonts.playfairDisplay(
                  fontSize: 28,
                  fontWeight: FontWeight.w700,
                  color: const Color(0xFFBBBBCC),
                  height: 1.2,
                ),
                decoration: InputDecoration(
                  hintText: 'Title of your inquiry',
                  hintStyle: GoogleFonts.playfairDisplay(
                    fontSize: 28,
                    fontWeight: FontWeight.w700,
                    color: const Color(0xFFCCCCDD),
                  ),
                  border: InputBorder.none,
                  isDense: true,
                  contentPadding: EdgeInsets.zero,
                ),
                textCapitalization: TextCapitalization.sentences,
                maxLines: 2,
                minLines: 1,
              ),
            ),

            // ── Body with dot-grid background ─────────────────────────────
            Expanded(
              child: Stack(
                children: [
                  // Dot grid painter
                  CustomPaint(
                    painter: _DotGridPainter(),
                    child: const SizedBox.expand(),
                  ),
                  // Body text field
                  Padding(
                    padding: const EdgeInsets.fromLTRB(18, 12, 18, 12),
                    child: TextField(
                      controller: bodyCtrl,
                      maxLines: null,
                      expands: true,
                      textAlignVertical: TextAlignVertical.top,
                      style: GoogleFonts.playfairDisplay(
                        fontSize: 17,
                        fontStyle: FontStyle.italic,
                        color: const Color(0xFFBBBBCC),
                        height: 1.7,
                      ),
                      decoration: InputDecoration(
                        hintText: 'Begin your long-form thought here. The AI will curate tasks and insights from your prose...',
                        hintStyle: GoogleFonts.playfairDisplay(
                          fontSize: 17,
                          fontStyle: FontStyle.italic,
                          color: const Color(0xFFCCCCDD),
                          height: 1.7,
                        ),
                        border: InputBorder.none,
                        isDense: true,
                        contentPadding: EdgeInsets.zero,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Dot grid painter ──────────────────────────────────────────────────────────

class _DotGridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFFCCCCDD).withOpacity(0.5)
      ..style = PaintingStyle.fill;

    const spacing = 22.0;
    const radius  = 1.2;

    for (double x = spacing; x < size.width; x += spacing) {
      for (double y = spacing; y < size.height; y += spacing) {
        canvas.drawCircle(Offset(x, y), radius, paint);
      }
    }
  }

  @override
  bool shouldRepaint(_DotGridPainter old) => false;
}

// ── AI insight sheet ──────────────────────────────────────────────────────────

class _InsightSheet extends StatelessWidget {
  const _InsightSheet();

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.all(12),
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AlexandriaTheme.surface,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const SparkleIcon(size: 16),
              const SizedBox(width: 6),
              Text(
                'AI ANALYSIS',
                style: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.2,
                  color: AlexandriaTheme.primary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Key Insights Found',
            style: GoogleFonts.playfairDisplay(
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: AlexandriaTheme.onSurface,
            ),
          ),
          const SizedBox(height: 16),
          _InsightItem(icon: Icons.task_alt, text: '2 action items extracted from your prose'),
          _InsightItem(icon: Icons.link, text: '3 cross-references suggested from your library'),
          _InsightItem(icon: Icons.schedule, text: 'Estimated 4 hours to complete this inquiry'),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('ADD TO SCHEDULE'),
            ),
          ),
          const SizedBox(height: 8),
          Center(
            child: TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Dismiss'),
            ),
          ),
        ],
      ),
    );
  }
}

class _InsightItem extends StatelessWidget {
  final IconData icon;
  final String text;
  const _InsightItem({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Container(
            width: 36, height: 36,
            decoration: BoxDecoration(
              color: AlexandriaTheme.primaryLight,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, size: 18, color: AlexandriaTheme.primary),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              text,
              style: GoogleFonts.inter(fontSize: 14, color: AlexandriaTheme.onSurface),
            ),
          ),
        ],
      ),
    );
  }
}
