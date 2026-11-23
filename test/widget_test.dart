import 'package:flutter_test/flutter_test.dart';

import 'package:book_compare/app.dart';
import 'package:book_compare/services/diff_repository.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('opens a chapter and shows the side-by-side comparison', (tester) async {
    await tester.runAsync(() => DiffRepository.instance.load());
    await tester.pumpWidget(const BookCompareApp());
    await tester.pump();

    expect(find.text('Book Compare'), findsOneWidget);
    expect(find.textContaining('differences in 18 chapters'), findsOneWidget);

    await tester.tap(find.text('Transcendental Knowledge'));
    await tester.pumpAndSettle();
    expect(find.text('Chapter 4'), findsOneWidget);

    await tester.tap(find.text('All changes in this chapter'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Change 1 of'), findsOneWidget);
    expect(find.text('1972 ORIGINAL'), findsWidgets);
    expect(find.text('REVISED EDITION'), findsWidgets);
  });
}
