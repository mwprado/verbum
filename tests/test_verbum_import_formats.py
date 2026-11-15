import unittest

from verbum.importers import IMPORT_FORMATS


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


if __name__ == "__main__":
    unittest.main()
