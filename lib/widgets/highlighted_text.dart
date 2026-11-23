import 'package:flutter/material.dart';

import '../models/diff_models.dart';

class HighlightedText extends StatelessWidget {
  final List<TextSegment> segments;
  final double fontSize;

  const HighlightedText({super.key, required this.segments, required this.fontSize});

  @override
  Widget build(BuildContext context) {
    final onSurface = Theme.of(context).colorScheme.onSurface;
    final spans = segments.map((segment) {
      final background = switch (segment.kind) {
        SegmentKind.same => null,
        SegmentKind.changed => const Color(0x40F9A825),
        SegmentKind.deleted => const Color(0x26C62828),
        SegmentKind.added => const Color(0x262E7D32),
      };
      return TextSpan(
        text: segment.text,
        style: TextStyle(
          color: onSurface,
          fontSize: fontSize,
          height: 1.45,
          backgroundColor: background,
        ),
      );
    }).toList();

    return RichText(
      text: TextSpan(children: spans),
      softWrap: true,
      textAlign: TextAlign.start,
    );
  }
}
