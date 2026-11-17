import gzip
import pickle
import tempfile
import unittest
from pathlib import Path

from verbum.core import manifest_info
from verbum.importers import pickle_entries, _pickle_metadata


class RochaPomboImportTests(unittest.TestCase):
    def make_source(self, directory):
        source = Path(directory) / "dicionario-rocha-pombo.pklz"
        payload = {
            "metadados": {
                "titulo": "Dicionário de Sinônimos da Língua Portuguesa",
                "autor": "Rocha Pombo",
                "edicao": "2ª edição",
                "editora": "Academia Brasileira de Letras",
                "ano": 2011,
                "formato": "rocha-pombo-cotejos/1.0",
            },
            "grupos": {
                1: {
                    "id": 1,
                    "pagina_pdf_inicio": 11,
                    "pagina_pdf_fim": 11,
                    "cabecalho": "A, para",
                    "termos_cabecalho": ["a", "para"],
                    "texto_explicativo": "Primeiro cotejo contextual.",
                },
                2: {
                    "id": 2,
                    "pagina_pdf_inicio": 12,
                    "pagina_pdf_fim": 13,
                    "cabecalho": "A, por",
                    "termos_cabecalho": ["a", "por"],
                    "texto_explicativo": "Segundo cotejo contextual.",
                },
            },
            "termos_para_grupos": {
                "a": [1, 2],
                "para": [1],
                "por": [2],
            },
            "estatisticas": {
                "cotejos": 2,
                "termos_cabecalho_unicos": 3,
            },
        }
        source.write_bytes(gzip.compress(pickle.dumps(payload, protocol=4)))
        return source

    def test_structured_container_yields_terms_not_top_level_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self.make_source(tmp)
            entries = list(pickle_entries(source))
            self.assertEqual(
                [entry["lemma"] for entry in entries],
                ["a", "para", "por"],
            )
            self.assertEqual(len(entries[0]["senses"]), 2)
            self.assertEqual(
                entries[0]["senses"][0]["source_group_id"], 1
            )
            self.assertNotIn(
                "metadados", [entry["lemma"] for entry in entries]
            )

    def test_rocha_pombo_metadata_is_identified(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self.make_source(tmp)
            metadata = _pickle_metadata(source)
            self.assertEqual(metadata["display_name"], "Rocha Pombo")
            self.assertEqual(metadata["function"], "synonyms")
            self.assertEqual(metadata["language"], "pt-br")
            self.assertEqual(metadata["origin"], "abl")
            self.assertEqual(metadata["edition"], "2")
            manifest = manifest_info(metadata)
            self.assertEqual(manifest["slug"], "pt-br-abl-synonyms-2")


if __name__ == "__main__":
    unittest.main()
