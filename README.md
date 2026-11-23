# Book Compare

An offline Flutter Android app for comparing editions of Srila Prabhupada's
books side by side. It shows only passages that differ, with the two texts
placed next to each other and the changed words highlighted. The app presents
the source texts without commentary or editorializing.

## Bundled books

| Book | Comparison | Chapters | Differences |
| --- | --- | ---: | ---: |
| Bhagavad-gita As It Is | 1972 Macmillan ↔ revised/post-1977 | 18 | 2,144 |
| Sri Caitanya-caritamrta | 1975 original ↔ Vedabase 2003 revised | 63 | 15,671 |
| Krsna: The Supreme Personality of Godhead | 1970 original ↔ Vedabase 2013 revised | 89 | 2,947 |

The app opens to a book picker. Each book has its own chapter list, section
list, edition labels, and source notes. Runtime is fully offline after
installation; there are no network calls or API dependencies.

## Source data

The datasets are built from the chapter-by-chapter ExamDiff reports linked from
[bookchanges.com](https://bookchanges.com/category/changes/). Each report has
two line-aligned panes: the left pane is the original side and the right pane
is the revised side. The parser supports both the older `d21`/`d22` markup used
by the Bhagavad-gita reports and the newer `file1`/`file2` markup used by the
Caitanya-caritamrta and Krsna Book reports.

Important limitations, also shown in the app's About screen:

- The source reports do not compare word-for-word synonyms.
- The text labelled "original" is not a facsimile of the printed book;
  scanning artefacts may remain.
- Krsna Book is continuous prose, so its changes are grouped as one passage
  per chapter.
- The app highlights differences; it does not adjudicate them.

## Project layout

- `lib/screens/books_screen.dart` — book picker
- `lib/screens/chapters_screen.dart` — chapter list for the selected book
- `lib/screens/section_list_screen.dart` — verse/passage list for a chapter
- `lib/screens/comparison_screen.dart` — side-by-side comparison
- `lib/widgets/` — hunk cards, highlight rendering, and legend
- `lib/models/diff_models.dart` — JSON models and parsing
- `lib/services/diff_repository.dart` — loads and caches bundled assets
- `assets/data/books.json` — book manifest
- `assets/data/*_diffs.json` — per-book diff datasets
- `tools/build_diff_data.py` — downloads and parses the source reports
- `test/` — data and widget tests

## Regenerating the datasets

The generated JSON is already included in `assets/data/`. You only need to run
the pipeline if you want to rebuild it from the online reports.

```bash
python -m pip install beautifulsoup4
python tools/build_diff_data.py
```

To rebuild only selected books:

```bash
python tools/build_diff_data.py --books bg
python tools/build_diff_data.py --books cc kb
```

The script downloads HTML reports to `tools/.cache/` on first run and then
parses them into `assets/data/`. To rebuild using only cached files:

```bash
python tools/build_diff_data.py --offline
```

`curl.exe` is used for downloads because it handles these source pages more
reliably than Python's default downloader. The cache is ignored by Git.

## Development

```bash
flutter pub get
flutter analyze
flutter test
```

Run on a connected arm64 Android device:

```bash
flutter run --target-platform android-arm64
```

Build a release APK:

```bash
flutter build apk --release --target-platform android-arm64
```

This build is arm64-only and requires Android 10 (API 29) or newer. The Gradle
configuration also filters native libraries to `arm64-v8a`, so a plain
`flutter build apk --release` produces the same single-ABI APK.

The APK is written to `build/app/outputs/flutter-apk/app-release.apk`.

## Highlight colors

- Amber: wording changed on both sides
- Red: words present only in the original edition
- Green: words present only in the revised edition
