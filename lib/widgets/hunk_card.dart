import 'package:flutter/material.dart';

import '../models/diff_models.dart';
import 'highlighted_text.dart';

class HunkCard extends StatelessWidget {
  final String reference;
  final DiffHunk hunk;
  final String originalLabel;
  final String revisedLabel;
  final double fontSize;
  final bool focused;

  const HunkCard({
    super.key,
    required this.reference,
    required this.hunk,
    required this.originalLabel,
    required this.revisedLabel,
    required this.fontSize,
    required this.focused,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Card(
      color: focused ? colorScheme.secondaryContainer.withValues(alpha: 0.45) : null,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Icon(Icons.compare_arrows, size: 16, color: colorScheme.primary),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    '$reference  ·  ${hunk.section}',
                    style: theme.textTheme.labelLarge?.copyWith(
                      color: colorScheme.primary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: _Pane(
                    label: originalLabel,
                    accent: const Color(0xFF8D6E63),
                    segments: hunk.original,
                    fontSize: fontSize,
                  ),
                ),
                Container(
                  width: 1,
                  color: theme.dividerColor,
                  margin: const EdgeInsets.symmetric(horizontal: 10),
                ),
                Expanded(
                  child: _Pane(
                    label: revisedLabel,
                    accent: colorScheme.primary,
                    segments: hunk.revised,
                    fontSize: fontSize,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _Pane extends StatelessWidget {
  final String label;
  final Color accent;
  final List<TextSegment> segments;
  final double fontSize;

  const _Pane({
    required this.label,
    required this.accent,
    required this.segments,
    required this.fontSize,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: theme.textTheme.labelSmall?.copyWith(
            color: accent,
            fontWeight: FontWeight.bold,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 6),
        if (segments.isEmpty)
          Text(
            '(no corresponding text)',
            style: theme.textTheme.bodySmall?.copyWith(fontStyle: FontStyle.italic),
          )
        else
          HighlightedText(segments: segments, fontSize: fontSize),
      ],
    );
  }
}
