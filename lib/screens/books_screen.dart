import 'package:flutter/material.dart';

import '../models/diff_models.dart';
import '../services/diff_repository.dart';
import 'about_screen.dart';
import 'chapters_screen.dart';

class BooksScreen extends StatelessWidget {
  const BooksScreen({super.key});

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
      body: FutureBuilder<List<BookSummary>>(
        future: DiffRepository.instance.loadBooks(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError || !snapshot.hasData) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text('Could not load the book list.\n${snapshot.error ?? ''}'),
              ),
            );
          }
          return _BookList(books: snapshot.data!);
        },
      ),
    );
  }
}

class _BookList extends StatelessWidget {
  final List<BookSummary> books;

  const _BookList({required this.books});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 18, 16, 10),
          child: Text(
            'Choose a book to compare',
            style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Text(
            'Each book compares the original edition with a later revised edition.',
            style: theme.textTheme.bodySmall,
          ),
        ),
        const SizedBox(height: 8),
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.only(bottom: 12),
            itemCount: books.length,
            separatorBuilder: (_, _) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final book = books[index];
              return ListTile(
                leading: CircleAvatar(
                  backgroundColor: theme.colorScheme.primaryContainer,
                  foregroundColor: theme.colorScheme.onPrimaryContainer,
                  child: const Icon(Icons.menu_book),
                ),
                title: Text(book.shortTitle),
                subtitle: Text(
                  '${book.originalEdition}  ↔  ${book.revisedEdition}\n'
                  '${book.hunkCount} differences · ${book.chapterCount} chapters',
                ),
                isThreeLine: true,
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => ChaptersScreen(bookId: book.id, summary: book),
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
