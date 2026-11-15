import tempfile
import unittest
from contextlib import closing
from verbum.core import Registry, connect_read
from verbum.media import get_media

class ResourceTests(unittest.TestCase):
    def test_independent_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = Registry(tmp)
            meta = dict(title="Demo", language="en", origin="demo", function="general", license="CC0")
            ref = dict(type="audio", archive="gb_hwd_pron", name="sample.mp3")
            result = reg.import_entries(meta, [dict(lemma="sample", media=[ref]), dict(lemma="other", media=[ref])],
                                        resource_loader=lambda *_: (b"ID3synthetic", "audio/mpeg"))
            self.assertEqual(result["format_version"], 2)
            hit = reg.search("sample", mode="exact")[0]
            self.assertEqual(get_media(reg, result["slug"], hit["entry_id"], 0), (b"ID3synthetic", "audio/mpeg"))
            with closing(connect_read(result["path"])) as db:
                self.assertEqual(db.execute("SELECT count(*) FROM resources").fetchone()[0], 1)
    def test_multiple_representations_preserve_original_and_prefer_open_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = Registry(tmp)
            meta = dict(title="Demo", language="en", origin="demo", function="general", license="CC0")
            ref = dict(type="audio", archive="demo", name="sample.mp3")

            def loader(*_):
                return {
                    "content": b"ID3-original",
                    "mime": "audio/mpeg",
                    "representations": [{
                        "role": "playback",
                        "content": b"OggS-open-opus",
                        "mime": "audio/ogg",
                        "codec": "opus",
                        "container": "ogg",
                        "lossy": True,
                        "preferred": True,
                    }],
                }

            result = reg.import_entries(
                meta,
                [dict(lemma="sample", media=[ref])],
                resource_loader=loader,
            )
            hit = reg.search("sample", mode="exact")[0]
            entry_ref = hit["entry"]["media"][0]

            self.assertEqual(
                get_media(reg, result["slug"], hit["entry_id"], 0),
                (b"OggS-open-opus", "audio/ogg"),
            )
            self.assertIn("original_sha256", entry_ref)
            self.assertEqual(entry_ref["original_mime"], "audio/mpeg")
            self.assertEqual(entry_ref["mime"], "audio/ogg")
            self.assertEqual(len(entry_ref["representations"]), 2)
            self.assertEqual(entry_ref["representations"][1]["codec"], "opus")

            with closing(connect_read(result["path"])) as db:
                self.assertEqual(db.execute("SELECT count(*) FROM resources").fetchone()[0], 2)

    def test_legacy_media_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = Registry(tmp)
            result = reg.import_entries(dict(title="Demo",language="en",origin="demo",function="general",license="CC0"),
                [dict(lemma="sample",media=[dict(type="audio",archive="gb_hwd_pron",name="sample.mp3")])])
            with self.assertRaises(ValueError):
                get_media(reg,result["slug"],1,0)
