import 'package:flutter/material.dart';

import 'screens/books_screen.dart';

class BookEditApp extends StatelessWidget {
  const BookEditApp({super.key});

  @override
  Widget build(BuildContext context) {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF9A5B16),
      brightness: Brightness.light,
    );

    return MaterialApp(
      title: 'Book edit',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: colorScheme,
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFFBF7EF),
        appBarTheme: AppBarTheme(
          backgroundColor: colorScheme.primaryContainer,
          foregroundColor: colorScheme.onPrimaryContainer,
          centerTitle: false,
        ),
        cardTheme: CardThemeData(
          elevation: 1,
          margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      // Android 15+ can draw edge to edge. Keep every route above the system
      // navigation bar (including the 3-button bar) while AppBar handles top inset.
      builder: (context, child) =>
          SafeArea(top: false, child: child ?? const SizedBox.shrink()),
      home: const BooksScreen(),
    );
  }
}
