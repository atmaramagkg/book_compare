import 'package:flutter/material.dart';

import '../models/diff_models.dart';
import 'comparison_screen.dart';

class SectionListScreen extends StatelessWidget {
  final ChapterDiff chapter;
  final DiffDataset dataset;

  const SectionListScreen({super.key, required this.chapter, required this.dataset});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text('${dataset.shortTitle} · ${chapter.numberLabel}'),
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 10),
            child: Text(
              chapter.title,
              style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Text(
              '${chapter.hunkCount} changes across '
              '${chapter.sectionCount} ${dataset.countLabel(chapter.sectionCount)}',
              style: theme.textTheme.bodySmall,
            ),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: ListView.separated(
              itemCount: chapter.sections.length + 1,
              separatorBuilder: (_, _) => const Divider(height: 1),
              itemBuilder: (context, index) {
                if (index == 0) {
                  return ListTile(
                    leading: CircleAvatar(
                      backgroundColor: theme.colorScheme.primaryContainer,
                      child: Icon(
                        Icons.select_all,
                        color: theme.colorScheme.onPrimaryContainer,
                      ),
                    ),
                    title: Text('All changes in this ${dataset.unitLabel}'),
                    subtitle: Text('${chapter.hunkCount} passages'),
                    onTap: () => _open(context, null),
                  );
                }
                final section = chapter.sections[index - 1];
                final reference = dataset.displayReference(section.reference);
                return ListTile(
                  leading: CircleAvatar(
                    backgroundColor: theme.colorScheme.primaryContainer,
                    foregroundColor: theme.colorScheme.onPrimaryContainer,
                    child: Text(
                      section.reference.split(RegExp(r'[.\s]')).last,
                      style: const TextStyle(fontSize: 12),
                    ),
                  ),
                  title: Text(reference),
                  subtitle: Text(
                    '${section.hunks.length} '
                    '${section.hunks.length == 1 ? 'change' : 'changes'}',
                  ),
                  onTap: () => _open(context, section.reference),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  void _open(BuildContext context, String? reference) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => ComparisonScreen(
          chapter: chapter,
          dataset: dataset,
          initialReference: reference,
        ),
      ),
    );
  }
}
