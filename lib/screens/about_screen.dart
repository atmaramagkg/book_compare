import 'package:flutter/material.dart';

import '../models/diff_models.dart';
import '../services/diff_repository.dart';

class AboutScreen extends StatelessWidget {
  final String? bookId;

  const AboutScreen({super.key, this.bookId});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final future = bookId == null ? null : DiffRepository.instance.loadBook(bookId!);

    return Scaffold(
      appBar: AppBar(title: const Text('About')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text('What this app shows', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          const Text(
            'This app displays side-by-side comparisons of original and later '
            'revised editions of Srila Prabhupada\'s books. Only passages that '
            'differ are shown. The texts are presented without taking a position '
            'on the dispute about the changes.',
          ),
          const SizedBox(height: 20),
          Text('How the comparisons were made', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          const Text(
            'The data comes from published chapter-by-chapter diff reports. '
            'Those reports were generated from Bhaktivedanta Vedabase texts. '
            'The source reports did not compare word-for-word synonyms, and the '
            'text labelled "original" is not a facsimile of the printed book. '
            'Scanning artefacts may remain.',
          ),
          const SizedBox(height: 20),
          if (future == null)
            _BookSources(theme: theme)
          else
            FutureBuilder<DiffDataset>(
              future: future,
              builder: (context, snapshot) {
                if (!snapshot.hasData) {
                  return const SizedBox(
                    height: 60,
                    child: Center(child: CircularProgressIndicator()),
                  );
                }
                return _BookDetails(dataset: snapshot.data!, theme: theme);
              },
            ),
          const SizedBox(height: 20),
          Text('Reading guide', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          const Text(
            'Amber highlight = wording changed on both sides. '
            'Red = words present only in the original edition. '
            'Green = words present only in the revised edition.',
          ),
        ],
      ),
    );
  }
}

class _BookDetails extends StatelessWidget {
  final DiffDataset dataset;
  final ThemeData theme;

  const _BookDetails({required this.dataset, required this.theme});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(dataset.book, style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),
        Text('${dataset.originalEdition}  ↔  ${dataset.revisedEdition}'),
        const SizedBox(height: 8),
        Text(
          '${dataset.hunkCount} differences across '
          '${dataset.chapterCount} chapters.',
        ),
        const SizedBox(height: 12),
        Text(dataset.sourceName, style: theme.textTheme.bodySmall),
        const SizedBox(height: 4),
        SelectableText(dataset.sourceUrl),
        const SizedBox(height: 8),
        Text(dataset.sourceNote, style: theme.textTheme.bodySmall),
      ],
    );
  }
}

class _BookSources extends StatelessWidget {
  final ThemeData theme;

  const _BookSources({required this.theme});

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<BookSummary>>(
      future: DiffRepository.instance.loadBooks(),
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const SizedBox(
            height: 60,
            child: Center(child: CircularProgressIndicator()),
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Books included', style: theme.textTheme.titleMedium),
            const SizedBox(height: 8),
            ...snapshot.data!.map(
              (book) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(
                  '${book.shortTitle}: ${book.originalEdition} ↔ '
                  '${book.revisedEdition}',
                ),
              ),
            ),
            const SelectableText(
              'https://bookchanges.com/category/changes/',
            ),
            const SizedBox(height: 20),
          ],
        );
      },
    );
  }
}
