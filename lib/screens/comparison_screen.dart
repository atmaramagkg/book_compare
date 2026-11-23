import 'package:flutter/material.dart';

import '../models/diff_models.dart';
import '../widgets/change_legend.dart';
import '../widgets/hunk_card.dart';
import 'about_screen.dart';

typedef IndexedHunk = ({String reference, DiffHunk hunk});

class ComparisonScreen extends StatefulWidget {
  final ChapterDiff chapter;
  final DiffDataset dataset;
  final String? initialReference;

  const ComparisonScreen({
    super.key,
    required this.chapter,
    required this.dataset,
    this.initialReference,
  });

  @override
  State<ComparisonScreen> createState() => _ComparisonScreenState();
}

class _ComparisonScreenState extends State<ComparisonScreen> {
  late final List<IndexedHunk> _all;
  late List<IndexedHunk> _visible;
  String? _selectedReference;
  double _fontSize = 14;
  int _focusedIndex = 0;
  final Map<String, GlobalKey> _keys = {};

  static const _fontSizes = [12.0, 14.0, 16.0, 18.0];

  @override
  void initState() {
    super.initState();
    _all = widget.chapter.sections
        .expand(
          (section) => section.hunks.map(
            (hunk) => (reference: section.reference, hunk: hunk),
          ),
        )
        .toList();
    _selectedReference = widget.initialReference;
    _visible = _selectedReference == null
        ? _all
        : _all.where((entry) => entry.reference == _selectedReference).toList();
  }

  void _filter(String? reference) {
    setState(() {
      _selectedReference = reference;
      _visible = reference == null
          ? _all
          : _all.where((entry) => entry.reference == reference).toList();
      _focusedIndex = 0;
    });
  }

  void _cycleFontSize() {
    final index = _fontSizes.indexOf(_fontSize);
    setState(() => _fontSize = _fontSizes[(index + 1) % _fontSizes.length]);
  }

  void _goTo(int index) {
    if (_visible.isEmpty) return;
    final next = index.clamp(0, _visible.length - 1);
    setState(() => _focusedIndex = next);
    final key = _keys[_visible[next].hunk.id];
    final context = key?.currentContext;
    if (context != null) {
      Scrollable.ensureVisible(
        context,
        alignment: 0.08,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final dataset = widget.dataset;
    final sections = widget.chapter.sections;

    return Scaffold(
      appBar: AppBar(
        title: Text('${widget.chapter.numberLabel} · side by side'),
        actions: [
          IconButton(
            icon: const Icon(Icons.text_fields),
            tooltip: 'Change text size (${_fontSize.toInt()} px)',
            onPressed: _cycleFontSize,
          ),
          IconButton(
            icon: const Icon(Icons.info_outline),
            tooltip: 'About',
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => AboutScreen(bookId: dataset.id),
              ),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(14, 10, 14, 8),
            color: theme.colorScheme.surface,
            child: ChangeLegend(
              originalLabel: dataset.originalLabel,
              revisedLabel: dataset.revisedLabel,
            ),
          ),
          SizedBox(
            height: 46,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              itemCount: sections.length + 1,
              separatorBuilder: (_, _) => const SizedBox(width: 6),
              itemBuilder: (context, index) {
                final String? reference =
                    index == 0 ? null : sections[index - 1].reference;
                final selected = _selectedReference == reference;
                return FilterChip(
                  label: Text(
                    reference == null
                        ? 'All'
                        : dataset.displayReference(reference),
                  ),
                  selected: selected,
                  onSelected: (_) => _filter(reference),
                );
              },
            ),
          ),
          const Divider(height: 1),
          Expanded(
            child: _visible.isEmpty
                ? const Center(child: Text('No differences in this selection.'))
                : ListView.builder(
                    padding: const EdgeInsets.only(bottom: 12),
                    itemCount: _visible.length,
                    itemBuilder: (context, index) {
                      final entry = _visible[index];
                      final key = _keys.putIfAbsent(
                        entry.hunk.id,
                        () => GlobalKey(),
                      );
                      return HunkCard(
                        key: key,
                        reference: dataset.displayReference(entry.reference),
                        hunk: entry.hunk,
                        originalLabel: dataset.originalLabel,
                        revisedLabel: dataset.revisedLabel,
                        fontSize: _fontSize,
                        focused: index == _focusedIndex,
                      );
                    },
                  ),
          ),
          Container(
            decoration: BoxDecoration(
              color: theme.colorScheme.surface,
              border: Border(top: BorderSide(color: theme.dividerColor)),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_upward),
                    tooltip: 'Previous change',
                    onPressed: _visible.isEmpty ? null : () => _goTo(_focusedIndex - 1),
                  ),
                  Text(
                    _visible.isEmpty
                        ? 'No changes'
                        : 'Change ${_focusedIndex + 1} of ${_visible.length}',
                    style: theme.textTheme.bodySmall,
                  ),
                  IconButton(
                    icon: const Icon(Icons.arrow_downward),
                    tooltip: 'Next change',
                    onPressed: _visible.isEmpty ? null : () => _goTo(_focusedIndex + 1),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
