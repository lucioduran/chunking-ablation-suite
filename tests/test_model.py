import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from chunking_suite.core import MODEL_ID, MODEL_REVISION
from chunking_suite.model import Encoder, download


class ModelTests(unittest.TestCase):
    def test_pinned_download(self):
        hub = MagicMock()
        hub.snapshot_download.return_value = "local/path"
        with patch.dict("sys.modules", {"huggingface_hub": hub}):
            self.assertEqual(download(Path("cache")), "local/path")
        kwargs = hub.snapshot_download.call_args.kwargs
        self.assertEqual(kwargs["repo_id"], MODEL_ID)
        self.assertEqual(kwargs["revision"], MODEL_REVISION)
        self.assertIn("model.safetensors", kwargs["allow_patterns"])

    def test_offline_model_and_encoding(self):
        torch, transformers = MagicMock(), MagicMock()
        encoded = {"input_ids": MagicMock(), "attention_mask": MagicMock()}
        encoded["input_ids"].shape = [1, 10]
        tokenizer = transformers.AutoTokenizer.from_pretrained.return_value
        tokenizer.return_value = encoded
        torch.nn.functional.normalize.return_value.tolist.return_value = [[1.0, 0.0]]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "weights").write_bytes(b"test-only")
            lock = {"weights": hashlib.sha256(b"test-only").hexdigest()}
            with (
                patch("chunking_suite.model.MODEL_FILES", lock),
                patch.dict("sys.modules", {"torch": torch, "transformers": transformers}),
            ):
                encoder = Encoder(root)
                self.assertEqual(encoder.encode([]), [])
                self.assertEqual(encoder.encode(["hello"]), [[1, 0]])
                self.assertEqual(encoder.encode(["hello"] * 17), [[1, 0], [1, 0]])
                self.assertFalse(tokenizer.call_args.kwargs["truncation"])
                self.assertTrue(
                    transformers.AutoModel.from_pretrained.call_args.kwargs["local_files_only"]
                )
                self.assertTrue(
                    transformers.AutoTokenizer.from_pretrained.call_args.kwargs["local_files_only"]
                )
                torch.set_num_threads.assert_called_once_with(2)
                encoded["input_ids"].shape = [1, 257]
                with self.assertRaises(ValueError):
                    encoder.encode(["too long"])
                (root / "weights").write_bytes(b"changed")
                with self.assertRaises(ValueError):
                    Encoder(root)

    def test_environment_metadata(self):
        from chunking_suite.experiment import environment

        with (
            patch("chunking_suite.experiment.importlib.metadata.version", return_value="test"),
            patch("chunking_suite.experiment.subprocess.check_output", return_value="test\n"),
            patch("chunking_suite.experiment.sys.platform", "darwin"),
        ):
            info = environment()
            self.assertEqual(info["cpu"], "test")
            self.assertTrue(info["git_dirty"])
        with (
            patch("chunking_suite.experiment.importlib.metadata.version", return_value="test"),
            patch("chunking_suite.experiment.subprocess.check_output", return_value="\n"),
            patch("chunking_suite.experiment.sys.platform", "linux"),
        ):
            self.assertFalse(environment()["git_dirty"])
