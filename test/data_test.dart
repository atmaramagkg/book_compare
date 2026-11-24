import 'package:flutter_test/flutter_test.dart';

import 'package:book_compare/models/diff_models.dart';
import 'package:book_compare/services/diff_repository.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('loads every bundled book', () async {
    final books = await DiffRepository.instance.loadBooks();
    expect(books.length, 7);
    expect(
      books.map((b) => b.id),
      containsAll(['bg', 'kb', 'cc', 'sb', 'nod', 'tlc', 'iso']),
    );

    for (final book in books) {
      final data = await DiffRepository.instance.loadBook(book.id);
      expect(data.chapters.length, book.chapterCount);
      expect(data.hunkCount, book.hunkCount);
      expect(data.hunkCount, greaterThan(0));
    }
  });

  test('local prose books align chapters rather than replacing whole chapters',
      () async {
    for (final id in ['nod', 'tlc']) {
      final data = await DiffRepository.instance.loadBook(id);
      expect(data.hunkCount, data.chapterCount);

      for (final chapter in data.chapters) {
        for (final hunk in chapter.allHunks) {
          expect(
            hunk.original.any((segment) => segment.kind == SegmentKind.same),
            isTrue,
            reason: '$id ${chapter.numberLabel} has no unchanged original text',
          );
          expect(
            hunk.revised.any((segment) => segment.kind == SegmentKind.same),
            isTrue,
            reason: '$id ${chapter.numberLabel} has no unchanged revised text',
          );
        }
      }
    }
  });

  test('Isopanisad compares Translation and Purport without markup', () async {
    final data = await DiffRepository.instance.loadBook('iso');
    expect(data.unitLabel, 'mantra');
    expect(data.unitLabelPlural, 'mantras');
    expect(data.referencePrefix, 'Īśo');

    final hunks = data.chapters.expand((c) => c.allHunks).toList();
    expect(
      hunks.map((h) => h.section),
      containsAll(['TRANSLATION', 'PURPORT']),
    );
    for (final hunk in hunks) {
      for (final segment in [...hunk.original, ...hunk.revised]) {
        expect(segment.text, isNot(contains('<em>')));
      }
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
