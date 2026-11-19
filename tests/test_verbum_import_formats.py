import unittest

from verbum.importers import (
    IMPORT_FORMATS,
    _is_luft_regency_container,
    _luft_regency_entries,
    _pickle_metadata,
)


class ImportFormatTests(unittest.TestCase):
    def test_bgl_and_pickle_allow_multiple_files(self):
        formats = {item["id"]: item for item in IMPORT_FORMATS}
        self.assertTrue(formats["bgl"]["multiple"])
        self.assertTrue(formats["pickle"]["multiple"])

    def test_other_importers_remain_single_source(self):
        formats = {item["id"]: item for item in IMPORT_FORMATS}
        self.assertFalse(formats["longman"].get("multiple", False))
        self.assertFalse(formats["json"].get("multiple", False))
        self.assertFalse(formats["jsonl"].get("multiple", False))

    def test_luft_container_is_not_treated_as_lemma_map(self):
        container = {
            "metadados": {
                "titulo": "Dicionário Prático de Regência Verbal",
                "tipo": "regencia_verbal",
            },
            "entradas": [
                {
                    "id": 12,
                    "lema": "assistir",
                    "classe_gramatical_ocr": "verbo",
                    "texto_ocr": "☆ a: assistir ao espetáculo. ☆ alguém: assistir o doente.",
                    "regencias_declaradas_ocr": ["a", "objeto direto"],
                    "estruturas_declaradas_ocr": ["assistir a algo", "assistir alguém"],
                    "preposicoes_candidatas": ["a"],
                    "pagina_pdf": 80,
                    "linha": 3,
                }
            ],
            "indice": {"assistir": [12]},
            "estatisticas": {"entradas": 1},
        }
        self.assertTrue(_is_luft_regency_container(container))
        entries = list(_luft_regency_entries(container))
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["lemma"], "assistir")
        self.assertIn("assistir ao espetáculo", entry["definition"])
        self.assertEqual(entry["grammar"]["pos"], ["verbo"])
        self.assertEqual(entry["regency"]["prepositions"], ["a"])
        self.assertNotIn("pagina_pdf", entry)
        self.assertNotIn("linha", entry)

    def test_luft_metadata_uses_regency_function(self):
        nominal = _pickle_metadata("dicionario-reg-nom-luft.pklz")
        verbal = _pickle_metadata("dicionario-reg-ver-luft.pklz")
        self.assertEqual(nominal["origin"], "luft")
        self.assertEqual(verbal["origin"], "luft")
        self.assertEqual(nominal["function"], "regency")
        self.assertEqual(verbal["function"], "regency")
        self.assertIn("Nominal", nominal["title"])
        self.assertIn("Verbal", verbal["title"])


if __name__ == "__main__":
    unittest.main()
