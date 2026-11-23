import 'package:flutter/material.dart';

class ChangeLegend extends StatelessWidget {
  final String originalLabel;
  final String revisedLabel;

  const ChangeLegend({
    super.key,
    this.originalLabel = 'original only',
    this.revisedLabel = 'revised only',
  });

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 12,
      runSpacing: 4,
      children: [
        const _LegendItem(color: Color(0x40F9A825), label: 'reworded'),
        _LegendItem(
          color: const Color(0x26C62828),
          label: '${originalLabel.toLowerCase().split(' ').first} only',
        ),
        _LegendItem(
          color: const Color(0x262E7D32),
          label: '${revisedLabel.toLowerCase().split(' ').first} only',
        ),
      ],
    );
  }
}

class _LegendItem extends StatelessWidget {
  final Color color;
  final String label;

  const _LegendItem({required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    final style = Theme.of(context).textTheme.bodySmall;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(3),
            border: Border.all(color: Theme.of(context).dividerColor),
          ),
        ),
        const SizedBox(width: 4),
        Text(label, style: style),
      ],
    );
  }
}
