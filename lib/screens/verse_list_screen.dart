import 'package:flutter/material.dart';

import '../models/diff_models.dart';
import 'comparison_screen.dart';

class VerseListScreen extends StatelessWidget {
  final ChapterDiff chapter;

  const VerseListScreen({super.key, required this.chapter});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text('Chapter ${chapter.chapter}'),
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
              '${chapter.hunkCount} changes across ${chapter.verseCount} verses',
              style: theme.textTheme.bodySmall,
            ),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: ListView.separated(
              itemCount: chapter.verses.length + 1,
              separatorBuilder: (_, _) => const Divider(height: 1),
              itemBuilder: (context, index) {
                if (index == 0) {
                  return ListTile(
                    leading: CircleAvatar(
                      backgroundColor: theme.colorScheme.primaryContainer,
                      child: Icon(Icons.select_all, color: theme.colorScheme.onPrimaryContainer),
                    ),
                    title: const Text('All changes in this chapter'),
                    subtitle: Text('${chapter.hunkCount} passages'),
                    onTap: () => _open(context, null),
                  );
                }
                final verse = chapter.verses[index - 1];
                return ListTile(
                  leading: CircleAvatar(
                    backgroundColor: theme.colorScheme.primaryContainer,
                    foregroundColor: theme.colorScheme.onPrimaryContainer,
                    child: Text(verse.reference.split('.').last),
                  ),
                  title: Text('BG ${verse.reference}'),
                  subtitle: Text('${verse.hunks.length} ${verse.hunks.length == 1 ? 'change' : 'changes'}'),
                  onTap: () => _open(context, verse.reference),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  void _open(BuildContext context, String? verse) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => ComparisonScreen(chapter: chapter, initialVerse: verse),
      ),
    );
  }
}
