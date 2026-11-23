enum SegmentKind { same, changed, deleted, added }

extension SegmentKindX on SegmentKind {
  String get label => switch (this) {
        SegmentKind.same => 'unchanged',
        SegmentKind.changed => 'reworded',
        SegmentKind.deleted => 'in the 1972 text only',
        SegmentKind.added => 'in the revised text only',
      };
}

class TextSegment {
  final String text;
  final SegmentKind kind;

  const TextSegment(this.text, this.kind);

  factory TextSegment.fromJson(Map<String, dynamic> json) {
    final kind = switch (json['k'] as String) {
      'chg' => SegmentKind.changed,
      'del' => SegmentKind.deleted,
      'add' => SegmentKind.added,
      _ => SegmentKind.same,
    };
    return TextSegment(json['t'] as String, kind);
  }
}

class DiffHunk {
  final String id;
  final String section;
  final List<TextSegment> original;
  final List<TextSegment> revised;

  const DiffHunk({
    required this.id,
    required this.section,
    required this.original,
    required this.revised,
  });

  factory DiffHunk.fromJson(Map<String, dynamic> json) => DiffHunk(
        id: json['id'] as String,
        section: json['section'] as String,
        original: (json['original'] as List<dynamic>)
            .map((e) => TextSegment.fromJson(e as Map<String, dynamic>))
            .toList(),
        revised: (json['revised'] as List<dynamic>)
            .map((e) => TextSegment.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  String get plainOriginal => original.map((s) => s.text).join();
  String get plainRevised => revised.map((s) => s.text).join();
}

class VerseDiff {
  final String reference;
  final List<DiffHunk> hunks;

  const VerseDiff({required this.reference, required this.hunks});

  factory VerseDiff.fromJson(Map<String, dynamic> json) => VerseDiff(
        reference: json['reference'] as String,
        hunks: (json['hunks'] as List<dynamic>)
            .map((e) => DiffHunk.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class ChapterDiff {
  final int chapter;
  final String title;
  final int verseCount;
  final int hunkCount;
  final List<VerseDiff> verses;

  const ChapterDiff({
    required this.chapter,
    required this.title,
    required this.verseCount,
    required this.hunkCount,
    required this.verses,
  });

  factory ChapterDiff.fromJson(Map<String, dynamic> json) => ChapterDiff(
        chapter: json['chapter'] as int,
        title: json['title'] as String,
        verseCount: json['verseCount'] as int,
        hunkCount: json['hunkCount'] as int,
        verses: (json['verses'] as List<dynamic>)
            .map((e) => VerseDiff.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  List<DiffHunk> get allHunks => verses.expand((v) => v.hunks).toList();
}

class DiffDataset {
  final String book;
  final String originalEdition;
  final String revisedEdition;
  final String sourceName;
  final String sourceUrl;
  final String sourceNote;
  final String generatedAt;
  final int hunkCount;
  final List<ChapterDiff> chapters;

  const DiffDataset({
    required this.book,
    required this.originalEdition,
    required this.revisedEdition,
    required this.sourceName,
    required this.sourceUrl,
    required this.sourceNote,
    required this.generatedAt,
    required this.hunkCount,
    required this.chapters,
  });

  factory DiffDataset.fromJson(Map<String, dynamic> json) {
    final source = json['source'] as Map<String, dynamic>;
    return DiffDataset(
      book: json['book'] as String,
      originalEdition: json['originalEdition'] as String,
      revisedEdition: json['revisedEdition'] as String,
      sourceName: source['name'] as String,
      sourceUrl: source['url'] as String,
      sourceNote: source['note'] as String,
      generatedAt: json['generatedAt'] as String,
      hunkCount: json['hunkCount'] as int,
      chapters: (json['chapters'] as List<dynamic>)
          .map((e) => ChapterDiff.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}
