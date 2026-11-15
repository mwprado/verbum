import sqlite3
import unittest

from verbum.resources import embed_resources


class MissingResourceTests(unittest.TestCase):
    def test_missing_source_media_is_preserved_without_aborting(self):
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE resources (sha256 TEXT PRIMARY KEY, mime TEXT NOT NULL, content BLOB NOT NULL)")

        def loader(archive, name):
            if name == "missing.mp3":
                return None
            return b"ID3demo", "audio/mpeg"

        payload = {
            "lemma": "demo",
            "media": [
                {"type": "audio", "archive": "exa_pron", "name": "missing.mp3"},
                {"type": "audio", "archive": "exa_pron", "name": "present.mp3"},
            ],
        }
        result = embed_resources(db, payload, loader, {})

        self.assertTrue(result["media"][0]["missing"])
        self.assertNotIn("sha256", result["media"][0])
        self.assertIn("sha256", result["media"][1])
        self.assertEqual(db.execute("SELECT count(*) FROM resources").fetchone()[0], 1)

    def test_invalid_present_media_still_fails(self):
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE resources (sha256 TEXT PRIMARY KEY, mime TEXT NOT NULL, content BLOB NOT NULL)")

        def loader(_archive, _name):
            return b"", "audio/mpeg"

        with self.assertRaises(ValueError):
            embed_resources(
                db,
                {"lemma": "demo", "media": [{"type": "audio", "archive": "exa_pron", "name": "bad.mp3"}]},
                loader,
                {},
            )


if __name__ == "__main__":
    unittest.main()
