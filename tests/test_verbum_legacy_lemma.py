import unittest

from verbum.importers import _clean_legacy_lemma, _legacy_entry


class LegacyLemmaNormalizationTests(unittest.TestCase):
    def test_dollar_sense_suffix_is_removed(self):
        self.assertEqual(_clean_legacy_lemma("Água$1$"), ("Água", 1))
        self.assertEqual(_clean_legacy_lemma("Água benta$2$"), ("Água benta", 2))

    def test_real_punctuation_is_preserved(self):
        self.assertEqual(_clean_legacy_lemma("C++"), ("C++", None))
        self.assertEqual(_clean_legacy_lemma("quê?"), ("quê?", None))
        self.assertEqual(_clean_legacy_lemma("$100"), ("$100", None))

    def test_lema_original_has_priority_over_marked_fields(self):
        entry = _legacy_entry({
            "lema_original": "Água",
            "palavra": "Água$1$",
            "definicao": "Substância líquida.",
        })
        self.assertEqual(entry["lemma"], "Água")
        self.assertEqual(entry["source_lemma"], "Água$1$")
        self.assertEqual(entry["sense_index"], 1)
        self.assertNotIn("homograph", entry)

    def test_source_marker_is_preserved_when_used_as_lemma(self):
        entry = _legacy_entry({
            "palavra": "Água benta$3$",
            "definicao": "Água benzida.",
        })
        self.assertEqual(entry["lemma"], "Água benta")
        self.assertEqual(entry["source_lemma"], "Água benta$3$")
        self.assertEqual(entry["sense_index"], 3)
        self.assertNotIn("homograph", entry)


if __name__ == "__main__":
    unittest.main()
