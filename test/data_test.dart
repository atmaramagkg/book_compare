import 'package:flutter_test/flutter_test.dart';

import 'package:book_compare/services/diff_repository.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('loads every bundled book', () async {
    final books = await DiffRepository.instance.loadBooks();
    expect(books.length, 3);
    expect(books.map((b) => b.id), containsAll(['bg', 'kb', 'cc']));

    for (final book in books) {
      final data = await DiffRepository.instance.loadBook(book.id);
      expect(data.chapters.length, book.chapterCount);
      expect(data.hunkCount, book.hunkCount);
      expect(data.hunkCount, greaterThan(0));
    }
  });
}
