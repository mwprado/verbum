import io
import json
import tempfile
import unittest
from pathlib import Path

from verbum_ldoce5.recover import official_exa_pron_url, recover_log


def mp3_fixture():
    # MPEG-1 Layer III, 128 kbps, 44.1 kHz: 417-byte frames.
    header = bytes((0xFF, 0xFB, 0x90, 0x00))
    frame = header + bytes(413)
    return frame + frame


class _Response:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, _limit):
        return self.data


class RecoveryTests(unittest.TestCase):
    def test_official_url_uses_exa_prons_basename(self):
        url = official_exa_pron_url(
            "p008_000/p008_00059/p008-000599672.mp3"
        )
        self.assertIn("/exaProns/p008-000599672.mp3", url)
        self.assertIn("version=1.2.93", url)

    def test_recover_log_writes_valid_audio_and_updates_jsonl(self):
        audio = mp3_fixture()

        def opener(request, timeout):
            self.assertEqual(timeout, 20)
            self.assertIn(
                "/exaProns/p008-000599672.mp3",
                request.full_url,
            )
            return _Response(audio)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            logs.mkdir()
            log = logs / "longman-unrecoverable-test.jsonl"
            log.write_text(
                json.dumps({
                    "record_type": "import",
                    "format": "verbum-unrecoverable-media-log",
                    "version": 1,
                    "source_format": "longman",
                    "source_path": "/tmp/ldoce5.data",
                    "count": 1,
                })
                + "\n"
                + json.dumps({
                    "record_type": "resource",
                    "archive": "exa_pron",
                    "name": "p008_000/p008_00059/p008-000599672.mp3",
                    "media_type": "audio",
                    "extension": ".mp3",
                    "reason": "unrecoverable media record",
                    "status": "pending",
                })
                + "\n",
                encoding="utf-8",
            )

            results = recover_log(log, opener=opener)
            self.assertEqual(results[0]["status"], "recovered")

            rows = [
                json.loads(line)
                for line in log.read_text(encoding="utf-8").splitlines()
            ]
            resource = rows[1]
            self.assertEqual(resource["status"], "recovered")
            recovered = Path(resource["recovered_path"])
            self.assertTrue(recovered.is_file())
            self.assertEqual(recovered.read_bytes(), audio)
            self.assertEqual(
                recovered,
                root / "recovery" / "longman" / "exa_pron"
                / "p008-000599672.mp3",
            )

    def test_extra_names_are_added_to_recovery_queue(self):
        audio = mp3_fixture()

        def opener(_request, timeout):
            return _Response(audio)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            logs.mkdir()
            log = logs / "longman-unrecoverable-test.jsonl"
            log.write_text(
                json.dumps({
                    "record_type": "import",
                    "format": "verbum-unrecoverable-media-log",
                    "version": 1,
                    "source_format": "longman",
                    "source_path": "/tmp/ldoce5.data",
                    "count": 0,
                }) + "\n",
                encoding="utf-8",
            )

            results = recover_log(
                log,
                opener=opener,
                extra_names=["p008-000599671.mp3"],
            )
            self.assertEqual(results[0]["status"], "recovered")
            rows = [
                json.loads(line)
                for line in log.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(rows[1]["name"], "p008-000599671.mp3")
            self.assertEqual(rows[1]["status"], "recovered")


if __name__ == "__main__":
    unittest.main()
