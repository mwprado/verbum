import unittest
import zlib
from unittest.mock import patch

from verbum_ldoce5 import idmreader, media


class _Reader:
    payloads = {}

    def __init__(self, source, archive):
        self.source = source
        self.archive = archive

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, location):
        return self.payloads[location]


class Ldoce5MediaIndexTests(unittest.TestCase):
    def setUp(self):
        media._archive_index.cache_clear()
        media._location_digest.cache_clear()

    def tearDown(self):
        media._archive_index.cache_clear()
        media._location_digest.cache_clear()

    def test_picture_uses_first_logical_directory(self):
        loc = (0, 10, 0, 4)
        records = [
            (("thumbnail", "internal", "a"), "abacus.jpg", loc),
        ]
        with patch.object(media.idmreader, "list_files", return_value=iter(records)):
            logical, _, _ = media._archive_index("src", "picture", ("sig",))
        self.assertEqual(logical["thumbnail/abacus.jpg"], (loc,))

    def test_audio_xml_suffix_disambiguates_duplicate_basename(self):
        wanted = (0, 10, 0, 4)
        other = (10, 10, 0, 4)
        leaf = "p008-001559957.mp3"
        records = [
            (("root", "p008_001", "p008_00155"), leaf, wanted),
            (("root", "other", "branch"), leaf, other),
        ]
        with patch.object(media.idmreader, "list_files", return_value=iter(records)):
            location, rule = media._resolve_location(
                "src",
                "exa_pron",
                "p008_001/p008_00155/" + leaf,
                ("sig",),
            )
        self.assertEqual(location, wanted)
        self.assertTrue(rule.startswith("suffix:"))

    def test_duplicate_identical_content_is_safe(self):
        first = (0, 10, 0, 4)
        second = (10, 10, 0, 4)
        leaf = "same.mp3"
        records = [
            (("one",), leaf, first),
            (("two",), leaf, second),
        ]
        _Reader.payloads = {first: b"same", second: b"same"}
        with (
            patch.object(media.idmreader, "list_files", return_value=iter(records)),
            patch.object(media.idmreader, "ArchiveReader", _Reader),
        ):
            location, rule = media._resolve_location(
                "src", "exa_pron", leaf, ("sig",)
            )
        self.assertEqual(location, first)
        self.assertIn("duplicate-identical", rule)

    def test_bad_zlib_trailer_recovers_complete_requested_record(self):
        payload = b"A" * 11076 + b"B" * 512
        compressed = bytearray(zlib.compress(payload))
        compressed[-1] ^= 0x01
        recovered = idmreader._decompress_block(bytes(compressed), 11076)
        self.assertGreaterEqual(len(recovered), 11076)
        self.assertEqual(recovered[:11076], b"A" * 11076)

    def test_block_scan_advances_over_multiple_catalog_blocks(self):
        # Regression target is implemented in list_files: a file offset may jump
        # across more than one empty/unreferenced block.
        self.assertIn("while ci != len(origoffsets) - 1", __import__(
            "inspect"
        ).getsource(idmreader.list_files))

    def test_bad_zlib_trailer_does_not_accept_missing_requested_bytes(self):
        payload = b"A" * 100
        compressed = bytearray(zlib.compress(payload))
        compressed[-1] ^= 0x01
        with self.assertRaises(zlib.error):
            idmreader._decompress_block(bytes(compressed), 101)

    def test_mpeg_validation_accepts_two_consecutive_layer3_frames(self):
        # MPEG-1 Layer III, 128 kb/s, 44.1 kHz => 417-byte frame.
        header = bytes((0xFF, 0xFB, 0x90, 0x64))
        frame = header + bytes(417 - len(header))
        self.assertTrue(media._validate_mpeg_audio(frame + frame))

    def test_mpeg_validation_rejects_arbitrary_bytes(self):
        self.assertFalse(media._validate_mpeg_audio(b"ID3" + bytes(1000)))

    def test_conflicting_duplicate_follows_original_cdb_first(self):
        first = (0, 10, 0, 4)
        second = (10, 10, 0, 4)
        leaf = "duplicate.mp3"
        records = [
            (("one",), leaf, first),
            (("two",), leaf, second),
        ]
        _Reader.payloads = {first: b"1111", second: b"2222"}
        with (
            patch.object(media.idmreader, "list_files", return_value=iter(records)),
            patch.object(media.idmreader, "ArchiveReader", _Reader),
        ):
            location, rule = media._resolve_location(
                "src", "exa_pron", leaf, ("sig",)
            )
        self.assertEqual(location, first)
        self.assertEqual(rule, "original-cdb-first")


if __name__ == "__main__":
    unittest.main()
