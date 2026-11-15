import tempfile
import unittest

from verbum.core import Registry


class SearchRankingTests(unittest.TestCase):
    def test_exact_lemma_precedes_prefixes(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = Registry(tmp)
            meta = {
                "title": "Demo",
                "language": "pt-br",
                "origin": "demo",
                "function": "general",
                "license": "CC0",
            }
            result = reg.import_entries(
                meta,
                [
                    {"lemma": "água benta", "definition": "prefixo 1"},
                    {"lemma": "água doce", "definition": "prefixo 2"},
                    {"lemma": "água", "definition": "exato"},
                    {"lemma": "aguá", "definition": "similar"},
                ],
            )

            hits = reg.search(
                "água",
                mode="smart",
                dictionary=result["slug"],
                limit=20,
            )

            self.assertTrue(hits)
            self.assertEqual(hits[0]["entry"]["lemma"], "água")
            self.assertEqual(hits[0]["match"], "exact")
            self.assertTrue(
                all(
                    hit["match"] != "exact"
                    for hit in hits[1:]
                    if hit["entry"]["lemma"] != "água"
                )
            )

    def test_all_exact_homographs_precede_prefixes(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = Registry(tmp)
            meta = {
                "title": "Demo",
                "language": "pt-br",
                "origin": "demo",
                "function": "general",
                "license": "CC0",
            }
            result = reg.import_entries(
                meta,
                [
                    {"lemma": "água", "homograph": 1, "definition": "exato 1"},
                    {"lemma": "água benta", "definition": "prefixo"},
                    {"lemma": "água", "homograph": 2, "definition": "exato 2"},
                ],
            )

            hits = reg.search(
                "água",
                mode="smart",
                dictionary=result["slug"],
                limit=20,
            )

            self.assertEqual(
                [hit["match"] for hit in hits[:2]],
                ["exact", "exact"],
            )
            self.assertEqual(
                [hit["entry"]["lemma"] for hit in hits[:2]],
                ["água", "água"],
            )
            self.assertEqual(hits[2]["entry"]["lemma"], "água benta")
            self.assertEqual(hits[2]["match"], "prefix")


if __name__ == "__main__":
    unittest.main()
