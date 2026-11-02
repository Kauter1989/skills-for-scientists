#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline unit tests for sci-literature-news scripts."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

import collect_literature as cl
import profile as prof


class ProfileTests(unittest.TestCase):
    def test_default_profile_round_trip_and_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.md"
            data = prof.default_profile(
                "Test Researcher",
                [
                    {
                        "id": "D1",
                        "direction": "Graph neural networks",
                        "query": "graph neural networks",
                        "notes": "",
                    }
                ],
            )
            data["preferences"]["last_confirmed"] = "2026-11-02"
            prof.save_profile(path, data)
            loaded = prof.load_profile(path)
            self.assertEqual(loaded["profile"]["name"], "Test Researcher")
            self.assertEqual(loaded["directions"][0]["query"], "graph neural networks")
            self.assertEqual(prof.validate(loaded, require_confirm=True), [])

    def test_validation_requires_query_terms(self):
        data = prof.default_profile(
            "Test",
            [{"id": "D1", "direction": "Направление", "query": "", "notes": ""}],
        )
        errors = prof.validate(data)
        self.assertTrue(any("Query terms" in error for error in errors))


class RankingTests(unittest.TestCase):
    def test_sjr_and_core_classification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sjr = root / "sjr.csv"
            core = root / "core.csv"
            with sjr.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["sourceid", "title", "issn", "year", "field", "field_code", "sjr", "quartile", "source"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "sourceid": "1",
                        "title": "Medical Image Analysis",
                        "issn": "1361-8415",
                        "year": "2025",
                        "field": "Computer Science",
                        "field_code": "1700",
                        "sjr": "2.1",
                        "quartile": "Q1",
                        "source": "SCImago SJR 2025",
                    }
                )
            with core.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["title", "acronym", "rank", "source"])
                writer.writerow(["Conference on Neural Information Processing Systems", "NeurIPS", "A*", "ICORE2026"])
            sjr_cache = cl.load_sjr_cache(sjr)
            core_cache = cl.load_core_cache(core)
            journal_work = {
                "venue": "Medical Image Analysis",
                "primary_location": {
                    "source": {"issn_l": "1361-8415", "issn": ["1361-8415"]}
                },
                "primary_topic": {"field": {"display_name": "Computer Science"}},
            }
            ranking = cl.lookup_sjr(journal_work, sjr_cache)
            self.assertEqual(ranking["quartile"], "Q1")
            conference_work = {"venue": "NeurIPS 2026"}
            core_ranking = cl.lookup_core(conference_work, core_cache)
            self.assertEqual(core_ranking["rank"], "A*")
            result = cl.classify(conference_work, sjr_cache, core_cache)
            self.assertEqual(result["category"], "a_star")


if __name__ == "__main__":
    unittest.main()