import 'dart:convert';

import 'package:flutter/services.dart';

import '../models/diff_models.dart';

class DiffRepository {
  DiffRepository._();

  static final instance = DiffRepository._();

  DiffDataset? _cached;

  Future<DiffDataset> load() async {
    final cached = _cached;
    if (cached != null) return cached;

    final raw = await rootBundle.loadString('assets/data/bg_diffs.json');
    final dataset = DiffDataset.fromJson(json.decode(raw) as Map<String, dynamic>);
    _cached = dataset;
    return dataset;
  }
}
