import unittest

from verbum.importers import _legacy_entry_optional


class LegacyEmptyRecordTests(unittest.TestCase):
    def test_empty_mapping_record_is_skipped(self):
        self.assertIsNone(_legacy_entry_optional({}, ""))

    def test_empty_sequence_record_is_skipped(self):
        self.assertIsNone(_legacy_entry_optional(["", None]))

    def test_blank_mapping_key_with_empty_record_is_skipped(self):
        self.assertIsNone(_legacy_entry_optional({}, "   "))

    def test_nonempty_malformed_record_still_fails(self):
        with self.assertRaisesRegex(ValueError, "lema"):
            _legacy_entry_optional({"metadata": "conteúdo sem lema"})

    def test_valid_mapping_key_is_not_skipped(self):
        entry = _legacy_entry_optional("", "água")
        self.assertEqual(entry["lemma"], "água")


if __name__ == "__main__":
    unittest.main()
