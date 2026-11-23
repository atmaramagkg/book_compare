# Book Compare

An offline Flutter Android app for comparing editions of Srila Prabhupada's
books side by side. It shows only passages that differ, with the two texts
placed next to each other and the changed words highlighted. The app presents
the source texts without commentary or editorializing.

## Current scope

- First bundled book: Bhagavad-gita
- Comparison: original 1972 text vs. revised/post-1977 text
- Chapters: all 18
- Bundled differences: 2,144 hunks (translations, purports, and introductions)
- Runtime: fully offline after installation; no network permission or API calls

## Source data

The bundled dataset is built from the chapter-by-chapter ExamDiff reports linked
from [bookchanges.com](https://bookchanges.com/bhagavad-gita-changes-complete-list/).
Each report compares the Bhaktivedanta Vedabase 2003 original text with
Vedabase 3.1 revised text. The reports are used as structured diff data: the
left pane is the original side and the right pane is the revised side.

Important limitations, also shown in the app's About screen:

- The source reports do not compare the word-for-word synonyms.
- The 2003 Vedabase text contains occasional scanning artefacts, so the original
  side is not a facsimile of the printed 1972 book.
- The app highlights differences; it does not adjudicate them.

## Project layout

- `lib/screens/` — chapter list, section list, side-by-side comparison, About
- `lib/widgets/` — hunk cards and highlighted text rendering
- `lib/models/diff_models.dart` — JSON models and parsing
- `lib/services/diff_repository.dart` — loads and caches the bundled asset
- `assets/data/bg_diffs.json` — first bundled book's diff dataset
- `tools/build_diff_data.py` — downloads and parses the source reports
- `test/` — data and widget tests

The app name is book-agnostic; `bg_diffs.json` is the first book-specific data
file. Additional books can be added with their own datasets.

## Regenerating the Bhagavad-gita dataset

The generated JSON is already included in `assets/data/`. You only need to run
the pipeline if you want to rebuild it from the online reports.

```bash
python -m pip install beautifulsoup4
python tools/build_diff_data.py
```

The script downloads the 18 HTML reports to `tools/.cache/` on first run and then
parses them into `assets/data/bg_diffs.json`. To rebuild using only files already
in the cache:

```bash
python tools/build_diff_data.py --offline
```

The downloaded HTML is kept in `tools/.cache/` and is ignored by Git.

## Development

```bash
flutter pub get
flutter analyze
flutter test
```

Run on a connected Android device or emulator:

```bash
flutter run
```

Build a release APK:

```bash
flutter build apk --release
```

The APK is written to `build/app/outputs/flutter-apk/app-release.apk`.

## Highlight colors

- Amber: wording changed on both sides
- Red: words present only in the 1972 original
- Green: words present only in the revised edition
