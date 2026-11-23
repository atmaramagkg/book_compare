import 'dart:convert';

import 'package:flutter/services.dart';

import '../models/diff_models.dart';

class DiffRepository {
  DiffRepository._();

  static final instance = DiffRepository._();

  static const _dataDir = 'assets/data/';

  List<BookSummary>? _books;
  final Map<String, DiffDataset> _datasets = {};

  Future<List<BookSummary>> loadBooks() async {
    final cached = _books;
    if (cached != null) return cached;

    final raw = await rootBundle.loadString('${_dataDir}books.json');
    final books = (json.decode(raw) as List<dynamic>)
        .map((e) => BookSummary.fromJson(e as Map<String, dynamic>))
        .toList();
    _books = books;
    return books;
  }

  Future<DiffDataset> loadBook(String id) async {
    final cached = _datasets[id];
    if (cached != null) return cached;

    final books = await loadBooks();
    final summary = books.where((b) => b.id == id).toList();
    if (summary.isEmpty) {
      throw ArgumentError('Unknown book id: $id');
    }

    final raw = await rootBundle.loadString('$_dataDir${summary.first.asset}');
    final dataset = DiffDataset.fromJson(json.decode(raw) as Map<String, dynamic>);
    _datasets[id] = dataset;
    return dataset;
  }
}
