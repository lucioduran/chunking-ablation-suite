"""Explicit download and offline CPU embedding adapter."""

import hashlib
import os
from pathlib import Path

from .core import MODEL_ID, MODEL_REVISION
from .model_lock import MODEL_FILES


def download(cache: Path) -> str:
    from huggingface_hub import snapshot_download

    return snapshot_download(
        repo_id=MODEL_ID,
        revision=MODEL_REVISION,
        cache_dir=str(cache),
        allow_patterns=[
            "config.json",
            "model.safetensors",
            "tokenizer.json",
            "tokenizer_config.json",
            "special_tokens_map.json",
            "vocab.txt",
        ],
    )


class Encoder:
    def __init__(self, model_path: Path):
        self.hashes = {
            name: hashlib.sha256((model_path / name).read_bytes()).hexdigest()
            for name in MODEL_FILES
        }
        if self.hashes != MODEL_FILES:
            raise ValueError("Model files differ from pinned snapshot")
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.torch = torch
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
        self.model = AutoModel.from_pretrained(model_path, local_files_only=True).to("cpu").eval()

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        result = []
        for offset in range(0, len(texts), 16):
            encoded = self.tokenizer(
                texts[offset : offset + 16], padding=True, truncation=False, return_tensors="pt"
            )
            if encoded["input_ids"].shape[1] > 256:
                raise ValueError("Embedding input exceeds 256 tokens; no truncation permitted")
            with self.torch.inference_mode():
                hidden = self.model(**encoded).last_hidden_state
                mask = encoded["attention_mask"].unsqueeze(-1)
                pooled = (hidden * mask).sum(1) / mask.sum(1)
                normalized = self.torch.nn.functional.normalize(pooled, p=2, dim=1)
            result.extend(normalized.tolist())
        return result
