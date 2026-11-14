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
    def test_legacy_media_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = Registry(tmp)
            result = reg.import_entries(dict(title="Demo",language="en",origin="demo",function="general",license="CC0"),
                [dict(lemma="sample",media=[dict(type="audio",archive="gb_hwd_pron",name="sample.mp3")])])
            with self.assertRaises(ValueError):
                get_media(reg,result["slug"],1,0)
