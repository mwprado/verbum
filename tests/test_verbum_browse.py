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
        self.assertIsNotNone(page["seek_entry_id"])
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


    def test_browse_entry_starts_at_first_word(self):
        hit = self.registry.browse_entry(self.imported["slug"])
        self.assertEqual(hit["entry"]["lemma"], "abacate")

    def test_browse_entry_moves_one_word_at_a_time(self):
        hit = self.registry.browse_entry(self.imported["slug"])
        hit = self.registry.browse_entry(
            self.imported["slug"], hit["entry_id"], direction=1
        )
        self.assertEqual(hit["entry"]["lemma"], "bola")
        hit = self.registry.browse_entry(
            self.imported["slug"], hit["entry_id"], direction=-1
        )
        self.assertEqual(hit["entry"]["lemma"], "abacate")

    def test_letter_jump_opens_first_word_of_letter(self):
        hit = self.registry.browse_entry(self.imported["slug"], letter="D")
        self.assertEqual(hit["entry"]["lemma"], "dado")

    def test_letter_without_entries_returns_none(self):
        self.assertIsNone(
            self.registry.browse_entry(self.imported["slug"], letter="Z")
        )

    def test_letter_a_includes_accented_initials(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = Registry(tmp)
            imported = registry.import_entries(
                {
                    "title": "Acentos",
                    "language": "pt-br",
                    "origin": "acentos",
                    "function": "general",
                    "license": "test",
                    "license_type": "unspecified",
                    "access": "local",
                },
                [
                    {"lemma": "Água", "definition": "A"},
                    {"lemma": "Bola", "definition": "B"},
                ],
            )
            hit = registry.browse_entry(imported["slug"], letter="A")
            self.assertEqual(hit["entry"]["lemma"], "Água")



    def test_navigation_includes_entries_before_a_and_after_z(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = Registry(tmp)
            imported = registry.import_entries(
                {
                    "title": "Limites",
                    "language": "pt-br",
                    "origin": "limites",
                    "function": "general",
                    "license": "test",
                    "license_type": "unspecified",
                    "access": "local",
                },
                [
                    {"lemma": "123", "definition": "Antes de A"},
                    {"lemma": "abacate", "definition": "A"},
                    {"lemma": "zebra", "definition": "Z"},
                    {"lemma": "Ωmega", "definition": "Depois de Z"},
                ],
            )

            first = registry.browse_entry(imported["slug"])
            self.assertEqual(first["entry"]["lemma"], "123")

            a = registry.browse_entry(imported["slug"], letter="A")
            self.assertEqual(a["entry"]["lemma"], "abacate")

            before_a = registry.browse_entry(
                imported["slug"], a["entry_id"], direction=-1
            )
            self.assertEqual(before_a["entry"]["lemma"], "123")

            z = registry.browse_entry(imported["slug"], letter="Z")
            self.assertEqual(z["entry"]["lemma"], "zebra")

            after_z = registry.browse_entry(
                imported["slug"], z["entry_id"], direction=1
            )
            self.assertEqual(after_z["entry"]["lemma"], "Ωmega")



if __name__ == "__main__":
    unittest.main()
