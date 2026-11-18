import tempfile
import unittest

from verbum.core import Registry


META = {
    "title": "Demo",
    "language": "pt-br",
    "origin": "demo",
    "function": "general",
    "license": "CC0",
}


class SearchRankingTests(unittest.TestCase):
    def test_exact_lemma_precedes_substrings(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = Registry(tmp)
            result = reg.import_entries(
                META,
                [
                    {"lemma": "água benta", "definition": "expressão 1"},
                    {"lemma": "água doce", "definition": "expressão 2"},
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
            self.assertEqual(hits[1]["match"], "phrase")
            self.assertEqual(hits[2]["match"], "phrase")

    def test_all_exact_homographs_precede_substrings(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = Registry(tmp)
            result = reg.import_entries(
                META,
                [
                    {"lemma": "água", "homograph": 1, "definition": "exato 1"},
                    {"lemma": "água benta", "definition": "substring"},
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
            self.assertEqual(hits[2]["match"], "phrase")

    def test_single_term_matches_inside_lemma(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = Registry(tmp)
            result = reg.import_entries(
                META,
                [
                    {"lemma": "mar", "definition": "exato"},
                    {"lemma": "marinho", "definition": "início"},
                    {"lemma": "submarino", "definition": "meio"},
                    {"lemma": "amar", "definition": "fim"},
                    {"lemma": "terra", "definition": "não corresponde"},
                ],
            )

            hits = reg.search(
                "mar",
                mode="smart",
                dictionary=result["slug"],
                limit=20,
            )

            self.assertEqual(hits[0]["entry"]["lemma"], "mar")
            self.assertEqual(hits[0]["match"], "exact")
            self.assertEqual(
                {hit["entry"]["lemma"] for hit in hits[1:4]},
                {"amar", "marinho", "submarino"},
            )
            self.assertTrue(all(hit["match"] == "phrase" for hit in hits[1:4]))

    def test_compound_query_ranks_phrase_all_terms_then_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = Registry(tmp)
            result = reg.import_entries(
                META,
                [
                    {"lemma": "água doce", "definition": "exato"},
                    {"lemma": "peixe de água doce", "definition": "frase contígua"},
                    {"lemma": "água de sabor doce", "definition": "termos separados"},
                    {"lemma": "doce água mineral", "definition": "ordem inversa"},
                    {"lemma": "água potável", "definition": "um termo"},
                    {"lemma": "doce de leite", "definition": "um termo"},
                ],
            )

            hits = reg.search(
                "água doce",
                mode="smart",
                dictionary=result["slug"],
                limit=20,
            )

            self.assertEqual(
                [hit["entry"]["lemma"] for hit in hits[:4]],
                [
                    "água doce",
                    "peixe de água doce",
                    "doce água mineral",
                    "água de sabor doce",
                ],
            )
            self.assertEqual(
                [hit["match"] for hit in hits[:4]],
                ["exact", "phrase", "all_terms", "all_terms"],
            )
            self.assertTrue(all(hit["match"] == "partial" for hit in hits[4:6]))

    def test_distinct_matching_terms_control_partial_relevance(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = Registry(tmp)
            result = reg.import_entries(
                META,
                [
                    {"lemma": "rio água clara", "definition": "dois termos"},
                    {"lemma": "rio largo", "definition": "um termo"},
                    {"lemma": "água mineral", "definition": "um termo"},
                ],
            )

            hits = reg.search(
                "rio água doce",
                mode="smart",
                dictionary=result["slug"],
                limit=20,
            )

            self.assertEqual(hits[0]["entry"]["lemma"], "rio água clara")
            self.assertEqual(hits[0]["match"], "partial")

    def test_dictionary_filter_is_applied_before_ranking(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = Registry(tmp)
            first = reg.import_entries(
                META,
                [{"lemma": "água", "definition": "primeiro"}],
            )
            second_meta = dict(META, origin="demo2", title="Demo 2")
            second = reg.import_entries(
                second_meta,
                [{"lemma": "água", "definition": "segundo"}],
            )

            hits = reg.search(
                "água",
                mode="smart",
                dictionary=second["slug"],
                limit=20,
            )

            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["dictionary"], second["slug"])
            self.assertNotEqual(hits[0]["dictionary"], first["slug"])


if __name__ == "__main__":
    unittest.main()
