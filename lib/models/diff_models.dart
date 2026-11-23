enum SegmentKind { same, changed, deleted, added }

extension SegmentKindX on SegmentKind {
  String get label => switch (this) {
        SegmentKind.same => 'unchanged',
        SegmentKind.changed => 'reworded',
        SegmentKind.deleted => 'present only in the original edition',
        SegmentKind.added => 'present only in the revised edition',
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

class SectionDiff {
  final String reference;
  final List<DiffHunk> hunks;

  const SectionDiff({required this.reference, required this.hunks});

  factory SectionDiff.fromJson(Map<String, dynamic> json) => SectionDiff(
        reference: json['reference'] as String,
        hunks: (json['hunks'] as List<dynamic>)
            .map((e) => DiffHunk.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class ChapterDiff {
  final int chapter;
  final String numberLabel;
  final String title;
  final int sectionCount;
  final int hunkCount;
  final List<SectionDiff> sections;

  const ChapterDiff({
    required this.chapter,
    required this.numberLabel,
    required this.title,
    required this.sectionCount,
    required this.hunkCount,
    required this.sections,
  });

  factory ChapterDiff.fromJson(Map<String, dynamic> json) => ChapterDiff(
        chapter: json['chapter'] as int,
        numberLabel: json['numberLabel'] as String,
        title: json['title'] as String,
        sectionCount: json['sectionCount'] as int,
        hunkCount: json['hunkCount'] as int,
        sections: (json['sections'] as List<dynamic>)
            .map((e) => SectionDiff.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  List<DiffHunk> get allHunks => sections.expand((s) => s.hunks).toList();
}

class BookSummary {
  final String id;
  final String title;
  final String shortTitle;
  final String asset;
  final String originalEdition;
  final String revisedEdition;
  final int chapterCount;
  final int hunkCount;

  const BookSummary({
    required this.id,
    required this.title,
    required this.shortTitle,
    required this.asset,
    required this.originalEdition,
    required this.revisedEdition,
    required this.chapterCount,
    required this.hunkCount,
  });

  factory BookSummary.fromJson(Map<String, dynamic> json) => BookSummary(
        id: json['id'] as String,
        title: json['title'] as String,
        shortTitle: json['shortTitle'] as String,
        asset: json['asset'] as String,
        originalEdition: json['originalEdition'] as String,
        revisedEdition: json['revisedEdition'] as String,
        chapterCount: json['chapterCount'] as int,
        hunkCount: json['hunkCount'] as int,
      );
}

class DiffDataset {
  final String id;
  final String book;
  final String shortTitle;
  final String originalEdition;
  final String revisedEdition;
  final String originalLabel;
  final String revisedLabel;
  final String referencePrefix;
  final String unitLabel;
  final String unitLabelPlural;
  final String sourceName;
  final String sourceUrl;
  final String sourceNote;
  final String generatedAt;
  final int chapterCount;
  final int sectionCount;
  final int hunkCount;
  final List<ChapterDiff> chapters;

  const DiffDataset({
    required this.id,
    required this.book,
    required this.shortTitle,
    required this.originalEdition,
    required this.revisedEdition,
    required this.originalLabel,
    required this.revisedLabel,
    required this.referencePrefix,
    required this.unitLabel,
    required this.unitLabelPlural,
    required this.sourceName,
    required this.sourceUrl,
    required this.sourceNote,
    required this.generatedAt,
    required this.chapterCount,
    required this.sectionCount,
    required this.hunkCount,
    required this.chapters,
  });

  factory DiffDataset.fromJson(Map<String, dynamic> json) {
    final source = json['source'] as Map<String, dynamic>;
    return DiffDataset(
      id: json['id'] as String,
      book: json['book'] as String,
      shortTitle: json['shortTitle'] as String,
      originalEdition: json['originalEdition'] as String,
      revisedEdition: json['revisedEdition'] as String,
      originalLabel: json['originalLabel'] as String,
      revisedLabel: json['revisedLabel'] as String,
      referencePrefix: json['referencePrefix'] as String,
      unitLabel: json['unitLabel'] as String,
      unitLabelPlural: json['unitLabelPlural'] as String,
      sourceName: source['name'] as String,
      sourceUrl: source['url'] as String,
      sourceNote: source['note'] as String,
      generatedAt: json['generatedAt'] as String,
      chapterCount: json['chapterCount'] as int,
      sectionCount: json['sectionCount'] as int,
      hunkCount: json['hunkCount'] as int,
      chapters: (json['chapters'] as List<dynamic>)
          .map((e) => ChapterDiff.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  String displayReference(String reference) =>
      referencePrefix.isEmpty ? reference : '$referencePrefix $reference';

  String countLabel(int count) => count == 1 ? unitLabel : unitLabelPlural;
}
