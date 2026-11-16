import gzip
import pickle
import tempfile
import unittest
from pathlib import Path

from verbum.importers import (
    _clean_houaiss_markup,
    _pickle_metadata,
    pickle_entries,
)


class HouaissImportTests(unittest.TestCase):
    def test_inline_rtf_controls_are_removed_but_angle_examples_remain(self):
        raw = (
            r"{\i abrev.} de {\f20\b\i aceite}; "
            r"{\super 1}{\f20\b\i alfa} <casa A;item 1a> "
            r"\'96 teste"
        )
        cleaned = _clean_houaiss_markup(raw)
        self.assertNotIn(r"\f20", cleaned)
        self.assertNotIn(r"\super", cleaned)
        self.assertNotIn("{", cleaned)
        self.assertIn("abrev.", cleaned)
        self.assertIn("aceite", cleaned)
        self.assertIn("<casa A;item 1a>", cleaned)
        self.assertIn("–", cleaned)
        self.assertNotIn(r"\\sp9", cleaned)

    def test_pickle_import_preserves_raw_description_and_cleans_display(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "houaiss_deah001.pklz"
            payload = {
                "teste": {
                    "descricao": r"{\i termo} {\f20\b definição}",
                    "outras_entradas": [],
                }
            }
            source.write_bytes(gzip.compress(pickle.dumps(payload, protocol=4)))
            entries = list(pickle_entries(source))
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["lemma"], "teste")
            self.assertEqual(entries[0]["definition"], "termo definição")
            self.assertIn(r"\f20", entries[0]["raw_definition"])
            self.assertIn(r"\f20", entries[0]["descricao"])

    def test_houaiss_metadata_is_recognized(self):
        metadata = _pickle_metadata("/tmp/houaiss_deah001.pklz")
        self.assertEqual(metadata["display_name"], "Houaiss")
        self.assertEqual(metadata["language"], "pt-br")
        self.assertEqual(metadata["origin"], "houaiss")


if __name__ == "__main__":
    unittest.main()
