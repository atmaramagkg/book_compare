import 'package:flutter_test/flutter_test.dart';

import 'package:book_compare/services/diff_repository.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('loads bundled diff data', () async {
    final data = await DiffRepository.instance.load();
    expect(data.chapters.length, 18);
    expect(data.hunkCount, greaterThan(2000));
  });
}
