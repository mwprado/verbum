import tempfile
import unittest
from pathlib import Path

from verbum.importers import _pickle_metadata


class LegacyMetadataTests(unittest.TestCase):
    def test_volp_filename_gets_orthographic_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dicionario-abl-volp.pklz"
            metadata = _pickle_metadata(path)
        self.assertEqual(metadata["title"], "VOLP")
        self.assertEqual(metadata["display_name"], "VOLP")
        self.assertEqual(metadata["language"], "pt-br")
        self.assertEqual(metadata["origin"], "abl")
        self.assertEqual(metadata["function"], "orthographic")


if __name__ == "__main__":
    unittest.main()
