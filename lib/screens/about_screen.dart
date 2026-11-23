import 'package:flutter/material.dart';

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('About')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text('What this app shows', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          const Text(
            'This app displays a side-by-side comparison of the 1972 Macmillan '
            'edition of Bhagavad-gita As It Is with the "Revised and Enlarged" '
            'edition published after 1977. Only passages that differ are shown. '
            'The app presents the texts side by side without taking a position '
            'on the dispute about the changes.',
          ),
          const SizedBox(height: 20),
          Text('How the comparison was made', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          const Text(
            'The data comes from published chapter-by-chapter diff reports. '
            'Those reports were generated from the Bhaktivedanta Vedabase 2003 '
            '(original edition) and Vedabase 3.1 (revised edition). The source '
            'reports did not compare the word-for-word synonyms, and the 2003 '
            'Vedabase text contains occasional scanning artefacts, so the '
            'original side is not a facsimile of the printed 1972 book.',
          ),
          const SizedBox(height: 20),
          Text('Source', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          const SelectableText(
            'https://bookchanges.com/bhagavad-gita-changes-complete-list/',
          ),
          const SizedBox(height: 20),
          Text('Reading guide', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          const Text(
            'Amber highlight = wording changed on both sides. '
            'Red = words present only in the 1972 text. '
            'Green = words present only in the revised text.',
          ),
        ],
      ),
    );
  }
}
