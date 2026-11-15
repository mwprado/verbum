import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from verbum.resources import embed_resources
from verbum.importers import _write_unrecoverable_log


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

    def test_corrupt_source_media_is_preserved_without_binary_payload(self):
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE resources (sha256 TEXT PRIMARY KEY, mime TEXT NOT NULL, content BLOB NOT NULL)")

        payload = {
            "lemma": "demo",
            "media": [
                {"type": "audio", "archive": "exa_pron", "name": "broken.mp3"},
            ],
        }
        result = embed_resources(
            db,
            payload,
            lambda *_: {"unavailable": True, "reason": "unrecoverable media record"},
            {},
        )

        ref = result["media"][0]
        self.assertTrue(ref["corrupt"])
        self.assertEqual(ref["corrupt_reason"], "unrecoverable media record")
        self.assertNotIn("sha256", ref)
        self.assertEqual(db.execute("SELECT count(*) FROM resources").fetchone()[0], 0)

    def test_unrecoverable_log_is_jsonl_recovery_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "ldoce5.data"
            source.mkdir()
            registry = SimpleNamespace(root=Path(tmp) / "verbum")
            result = {
                "slug": "en-longman-learner-5",
                "path": str(Path(tmp) / "dictionary.vlf"),
            }
            corrupt = {
                ("exa_pron", "a/broken.mp3"): "unrecoverable media record",
                ("picture", "thumbnail/broken.jpg"): "empty or truncated media record",
            }

            path = Path(_write_unrecoverable_log(registry, source, result, corrupt))
            self.assertTrue(path.is_file())
            self.assertEqual(path.parent, registry.root / "logs")

            records = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(records[0]["record_type"], "import")
            self.assertEqual(records[0]["count"], 2)
            self.assertEqual(records[0]["source_path"], str(source.resolve()))
            self.assertEqual(records[1]["record_type"], "resource")
            self.assertEqual(records[1]["status"], "pending")
            self.assertEqual(
                {(r["archive"], r["name"]) for r in records[1:]},
                {
                    ("exa_pron", "a/broken.mp3"),
                    ("picture", "thumbnail/broken.jpg"),
                },
            )

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
