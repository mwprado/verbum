import tempfile
import unittest

from verbum.core import Registry


class DictionaryBrowseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry = Registry(self.tmp.name)
        metadata = {
            "title": "Teste",
            "language": "pt-br",
            "origin": "teste",
            "function": "general",
            "license": "test",
            "license_type": "unspecified",
            "access": "local",
        }
        entries = [
            {"lemma": "casa", "definition": "C"},
            {"lemma": "bola", "definition": "B"},
            {"lemma": "dado", "definition": "D"},
            {"lemma": "abacate", "definition": "A"},
            {"lemma": "elefante", "definition": "E"},
        ]
        self.imported = self.registry.import_entries(metadata, entries)

    def tearDown(self):
        self.tmp.cleanup()

    def test_browse_is_ordered_and_paginated(self):
        page = self.registry.browse(
            self.imported["slug"],
            page=0,
            page_size=2,
        )
        self.assertEqual(page["total"], 5)
        self.assertEqual(page["pages"], 3)
        self.assertEqual(
            [hit["entry"]["lemma"] for hit in page["hits"]],
            ["abacate", "bola"],
        )

        page = self.registry.browse(
            self.imported["slug"],
            page=1,
            page_size=2,
        )
        self.assertEqual(
            [hit["entry"]["lemma"] for hit in page["hits"]],
            ["casa", "dado"],
        )

    def test_browse_clamps_page_after_end(self):
        page = self.registry.browse(
            self.imported["slug"],
            page=99,
            page_size=2,
        )
        self.assertEqual(page["page"], 2)
        self.assertEqual(
            [hit["entry"]["lemma"] for hit in page["hits"]],
            ["elefante"],
        )

    def test_seek_repositions_to_page_near_requested_headword(self):
        page = self.registry.browse(
            self.imported["slug"],
            page=0,
            page_size=2,
            seek="dado",
        )
        self.assertEqual(page["page"], 1)
        self.assertEqual(page["seek"], "dado")
        self.assertEqual(
            [hit["entry"]["lemma"] for hit in page["hits"]],
            ["casa", "dado"],
        )

    def test_seek_after_last_entry_clamps_to_last_page(self):
        page = self.registry.browse(
            self.imported["slug"],
            page=0,
            page_size=2,
            seek="zzzz",
        )
        self.assertEqual(page["page"], 2)
        self.assertEqual(
            [hit["entry"]["lemma"] for hit in page["hits"]],
            ["elefante"],
        )


if __name__ == "__main__":
    unittest.main()
