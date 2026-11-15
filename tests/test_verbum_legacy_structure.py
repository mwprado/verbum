import unittest

from verbum.importers import _structure_legacy_definition


class LegacyStructureTests(unittest.TestCase):
    def test_etymology_grammar_and_numbered_senses_are_recovered(self):
        raw = (
            "[Do lat. aqua.] Substantivo feminino. "
            "1. Primeiro sentido. "
            "2. Segundo sentido."
        )
        entry = _structure_legacy_definition({"lemma": "água", "definition": raw})
        self.assertEqual(entry["etymology"], "Do lat. aqua.")
        self.assertEqual(entry["grammar"]["pos"], ["Substantivo feminino"])
        self.assertEqual([s["index"] for s in entry["senses"]], [1, 2])
        self.assertEqual(entry["senses"][0]["definitions"], ["Primeiro sentido."])
        self.assertEqual(entry["raw_definition"], raw)
        self.assertNotIn("definition", entry)

    def test_numbering_reset_stops_before_embedded_entry(self):
        raw = (
            "Substantivo feminino. "
            "1. Primeiro sentido. "
            "2. Segundo sentido. "
            "Água benta. 1. Entrada separada."
        )
        entry = _structure_legacy_definition({"lemma": "água", "definition": raw})
        self.assertEqual(len(entry["senses"]), 2)
        self.assertNotIn("Água benta", entry["senses"][1]["definitions"][0])
        self.assertTrue(entry["legacy_tail"].startswith("Água benta. 1."))
        self.assertIn("1. Entrada separada.", entry["legacy_tail"])

    def test_non_sequential_numbers_are_not_guessed_as_senses(self):
        raw = "Texto histórico de 1913. 7. referência isolada."
        entry = _structure_legacy_definition({"lemma": "teste", "definition": raw})
        self.assertEqual(entry["definition"], raw)
        self.assertNotIn("senses", entry)


if __name__ == "__main__":
    unittest.main()
