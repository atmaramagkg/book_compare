import 'package:flutter_test/flutter_test.dart';

import 'package:book_compare/services/diff_repository.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('loads every bundled book', () async {
    final books = await DiffRepository.instance.loadBooks();
    expect(books.length, 4);
    expect(books.map((b) => b.id), containsAll(['bg', 'kb', 'cc', 'sb']));

    for (final book in books) {
      final data = await DiffRepository.instance.loadBook(book.id);
      expect(data.chapters.length, book.chapterCount);
      expect(data.hunkCount, book.hunkCount);
      expect(data.hunkCount, greaterThan(0));
    }
  });

  test('Bhagavatam dataset stops at the lifetime-published text', () async {
    final data = await DiffRepository.instance.loadBook('sb');
    expect(data.chapters.last.numberLabel, '10.13');
    expect(data.chapters.any((c) => c.numberLabel.startsWith('11.')), isFalse);
    expect(data.referencePrefix, 'SB');
    expect(data.sourceNote, contains('Cantos 11-12'));
  });
}
