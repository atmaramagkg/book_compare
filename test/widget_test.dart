import 'package:flutter_test/flutter_test.dart';

import 'package:book_compare/app.dart';
import 'package:book_compare/services/diff_repository.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('opens a book, chapter, and side-by-side comparison', (tester) async {
    await tester.runAsync(() => DiffRepository.instance.loadBooks());
    await tester.runAsync(() => DiffRepository.instance.loadBook('bg'));
    await tester.pumpWidget(const BookEditApp());
    await tester.pump();

    expect(find.text('Book edit'), findsOneWidget);
    expect(find.text('Bhagavad-gita'), findsOneWidget);

    await tester.tap(find.text('Bhagavad-gita'));
    await tester.pumpAndSettle();
    expect(find.textContaining('differences in 18 chapters'), findsOneWidget);

    await tester.tap(find.text('Transcendental Knowledge'));
    await tester.pumpAndSettle();
    expect(find.textContaining('changes across'), findsOneWidget);

    await tester.tap(find.text('All changes in this verse'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Change 1 of'), findsOneWidget);
    expect(find.text('1972 ORIGINAL'), findsWidgets);
    expect(find.text('REVISED EDITION'), findsWidgets);
  });
}
