import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chunking_suite.cli import main
from chunking_suite.core import digest
from chunking_suite.experiment import evaluate, run, verify


class FakeEncoder:
    def __init__(self, path=None):
        self.hashes = {"fake": "test-only"}

    def encode(self, texts):
        return [[1.0, int(digest(text)[:6], 16) / 0xFFFFFF] for text in texts]


class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = {
            "version": 1,
            "documents": [
                {
                    "id": "a",
                    "kind": "code",
                    "split": "dev",
                    "blocks": [
                        {"section": "s", "text": "alpha beta"},
                        {"section": "t", "text": "gamma delta"},
                    ],
                }
            ],
            "queries": [
                {"id": "q", "doc_id": "a", "split": "dev", "text": "alpha?", "evidence": [[0, 5]]}
            ],
        }
        cls.report = evaluate(cls.data, "dev", FakeEncoder(), {"test_only": True})

    def test_replay(self):
        self.assertTrue(verify(self.report, self.data)["verified"])
        with self.assertRaises(ValueError):
            evaluate(self.data, "eval", FakeEncoder(), {})

    def test_tampering(self):
        mutations = [
            lambda r: r.update(data_hash="bad"),
            lambda r: r.update(query_vectors=[]),
            lambda r: r.update(runs=[]),
            lambda r: r["block_vectors"].update(a=[]),
            lambda r: r["runs"][0]["chunks"][0].update(text="bad"),
            lambda r: r["runs"][0]["rows"][0].update(query_id="bad"),
            lambda r: r["runs"][0]["rows"][0]["metrics"].update(complete_at_3=9),
            lambda r: r["runs"][0]["costs"]["code"].update(chunks=999),
            lambda r: r["runs"][0].update(summary={}),
            lambda r: r.update(contrasts=[]),
        ]
        for change in mutations:
            report = copy.deepcopy(self.report)
            change(report)
            with self.subTest(change=change), self.assertRaises(ValueError):
                verify(report, self.data)

    def test_run_files_and_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "input.json"
            data.write_text(json.dumps(self.data), encoding="utf-8")
            with (
                patch("chunking_suite.experiment.Encoder", FakeEncoder),
                patch("chunking_suite.experiment.environment", return_value={"test_only": True}),
            ):
                summary = run(data, root, root / "result", "dev")
                self.assertEqual(summary["split"], "dev")
                with self.assertRaises(FileExistsError):
                    run(data, root, root / "result", "dev")
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(
                        main(
                            [
                                "verify",
                                "--data",
                                str(data),
                                "--report",
                                str(root / "result/report.json"),
                            ]
                        ),
                        0,
                    )
                    self.assertEqual(
                        main(
                            [
                                "run",
                                "--data",
                                str(data),
                                "--model-path",
                                str(root),
                                "--split",
                                "dev",
                                "--output",
                                str(root / "again"),
                            ]
                        ),
                        0,
                    )
                    self.assertEqual(main(["verify", "--report", str(root / "absent")]), 2)
            with (
                patch("chunking_suite.cli.download", return_value="cache/path"),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(main(["download"]), 0)
