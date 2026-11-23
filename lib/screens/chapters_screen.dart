import 'package:flutter/material.dart';

import '../models/diff_models.dart';
import '../services/diff_repository.dart';
import 'about_screen.dart';
import 'verse_list_screen.dart';

class ChaptersScreen extends StatelessWidget {
  const ChaptersScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Book Compare'),
        actions: [
          IconButton(
            icon: const Icon(Icons.info_outline),
            tooltip: 'About this app',
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const AboutScreen()),
            ),
          ),
        ],
      ),
      body: FutureBuilder<DiffDataset>(
        future: DiffRepository.instance.load(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError || !snapshot.hasData) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text('Could not load the comparison data.\n${snapshot.error ?? ''}'),
              ),
            );
          }
          return _ChaptersList(dataset: snapshot.data!);
        },
      ),
    );
  }
}

class _ChaptersList extends StatelessWidget {
  final DiffDataset dataset;

  const _ChaptersList({required this.dataset});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 18),
          decoration: BoxDecoration(
            color: theme.colorScheme.primaryContainer.withValues(alpha: 0.55),
            border: Border(bottom: BorderSide(color: theme.dividerColor)),
          ),
          child: Text(
            '${dataset.book}\n'
            '${dataset.originalEdition}  ↔  ${dataset.revisedEdition}\n'
            '${dataset.hunkCount} differences in ${dataset.chapters.length} chapters',
            style: theme.textTheme.bodyMedium?.copyWith(height: 1.5),
          ),
        ),
        Expanded(
          child: ListView.builder(
            itemCount: dataset.chapters.length,
            itemBuilder: (context, index) {
              final chapter = dataset.chapters[index];
              return ListTile(
                leading: CircleAvatar(
                  backgroundColor: theme.colorScheme.primary,
                  foregroundColor: theme.colorScheme.onPrimary,
                  child: Text('${chapter.chapter}'),
                ),
                title: Text(chapter.title),
                subtitle: Text('${chapter.hunkCount} changes · ${chapter.verseCount} verses'),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => VerseListScreen(chapter: chapter),
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}
