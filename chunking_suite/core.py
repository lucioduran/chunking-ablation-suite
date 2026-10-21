"""Validated fixtures, offset-preserving chunking, and evidence-span metrics."""

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def fields(value: Any, expected: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"Expected fields: {sorted(expected)}")


def load_data(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    fields(data, {"version", "documents", "queries"})
    if data["version"] != 1 or not data["documents"] or not data["queries"]:
        raise ValueError("Unsupported version or empty dataset")
    docs = {}
    for doc in data["documents"]:
        fields(doc, {"id", "kind", "split", "blocks"})
        if not isinstance(doc["id"], str) or not doc["id"] or doc["id"] in docs:
            raise ValueError("Invalid or duplicate document ID")
        if doc["kind"] not in {"code", "table", "cross_reference"}:
            raise ValueError("Invalid document kind")
        if doc["split"] not in {"dev", "eval"} or not doc["blocks"]:
            raise ValueError("Invalid split or empty blocks")
        for block in doc["blocks"]:
            fields(block, {"section", "text"})
            if any(not isinstance(block[k], str) or not block[k].strip() for k in block):
                raise ValueError("Block fields must be nonempty strings")
        docs[doc["id"]] = doc
    ids = set()
    for query in data["queries"]:
        fields(query, {"id", "doc_id", "split", "text", "evidence"})
        if not isinstance(query["id"], str) or not query["id"] or query["id"] in ids:
            raise ValueError("Invalid or duplicate query ID")
        ids.add(query["id"])
        if query["doc_id"] not in docs or query["split"] != docs[query["doc_id"]]["split"]:
            raise ValueError("Missing document or split leakage")
        if not isinstance(query["text"], str) or not query["text"].strip():
            raise ValueError("Empty query")
        if not isinstance(query["evidence"], list) or not query["evidence"]:
            raise ValueError("Missing evidence")
        text = document_text(docs[query["doc_id"]])
        for span in query["evidence"]:
            if (
                not isinstance(span, list)
                or len(span) != 2
                or any(type(x) is not int for x in span)
                or not 0 <= span[0] < span[1] <= len(text)
            ):
                raise ValueError("Invalid evidence span")
    return data


def document_text(doc: dict) -> str:
    return "\n\n".join(block["text"] for block in doc["blocks"])


def block_spans(doc: dict) -> list[tuple[int, int]]:
    spans = []
    start = 0
    for block in doc["blocks"]:
        end = start + len(block["text"])
        spans.append((start, end))
        start = end + 2
    return spans


def cosine(a: list[float], b: list[float]) -> float:
    if not a or len(a) != len(b) or any(not math.isfinite(x) for x in a + b):
        raise ValueError("Vectors must have matching nonzero dimensions and finite values")
    norm = math.sqrt(sum(x * x for x in a) * sum(x * x for x in b))
    if norm == 0:
        raise ValueError("Zero vector")
    return sum(x * y for x, y in zip(a, b, strict=True)) / norm


def configurations() -> list[dict]:
    configs = []
    for method in ("fixed", "structure", "semantic"):
        for size in (64, 96):
            configs.append(
                {
                    "id": f"{method}-{size}",
                    "method": method,
                    "size": size,
                    "overlap": 0,
                    "threshold": 0.5,
                }
            )
    configs.append(
        {"id": "fixed-64-overlap16", "method": "fixed", "size": 64, "overlap": 16, "threshold": 0.5}
    )
    configs.append(
        {
            "id": "semantic-64-threshold07",
            "method": "semantic",
            "size": 64,
            "overlap": 0,
            "threshold": 0.7,
        }
    )
    return configs


def chunk(doc: dict, config: dict, vectors: list[list[float]]) -> list[dict]:
    method, size, overlap = config["method"], config["size"], config["overlap"]
    if method not in {"fixed", "structure", "semantic"}:
        raise ValueError("Unknown method")
    if type(size) is not int or size < 1 or type(overlap) is not int or not 0 <= overlap < size:
        raise ValueError("Invalid size or overlap")
    if method != "fixed" and overlap != 0:
        raise ValueError("Overlap is only supported for fixed windows")
    if not 0 <= config["threshold"] <= 1:
        raise ValueError("Threshold must be between zero and one")
    text = document_text(doc)
    words = list(re.finditer(r"\S+", text))
    if not words:
        raise ValueError("Empty document")
    ranges = []
    if method == "fixed":
        for i in range(0, len(words), size - overlap):
            end = min(i + size, len(words))
            ranges.append((words[i].start(), words[end - 1].end()))
            if end == len(words):
                break
    else:
        spans = block_spans(doc)
        if method == "semantic" and len(vectors) != len(spans):
            raise ValueError("Expected one vector per block")
        start, end = spans[0]
        count = len(text[start:end].split())
        for i, (left, right) in enumerate(spans[1:], 1):
            added = len(text[left:right].split())
            boundary = (
                doc["blocks"][i]["section"] != doc["blocks"][i - 1]["section"]
                if method == "structure"
                else cosine(vectors[i - 1], vectors[i]) < config["threshold"]
            )
            if boundary or count + added > size:
                ranges.append((start, end))
                start, count = left, 0
            end, count = right, count + added
        ranges.append((start, end))
    return [
        {
            "id": f"{doc['id']}:{i}",
            "doc_id": doc["id"],
            "kind": doc["kind"],
            "start": a,
            "end": b,
            "text": text[a:b],
        }
        for i, (a, b) in enumerate(ranges)
    ]


def covered(span: list[int], ranges: list[tuple[int, int]]) -> bool:
    cursor = span[0]
    for start, end in sorted(ranges):
        if start > cursor:
            break
        cursor = max(cursor, end)
        if cursor >= span[1]:
            return True
    return False


def score(query: dict, ranking: list[dict], k: int = 3) -> dict:
    if k < 1:
        raise ValueError("k must be positive")
    ranges: list[tuple[int, int]] = []
    recall = 0.0
    reciprocal = 0.0
    for rank, item in enumerate(ranking[:k], 1):
        if item["doc_id"] == query["doc_id"]:
            ranges.append((item["start"], item["end"]))
        recall = sum(covered(s, ranges) for s in query["evidence"]) / len(query["evidence"])
        if recall == 1 and reciprocal == 0:
            reciprocal = 1 / rank
    return {
        "evidence_recall_at_3": recall,
        "complete_at_3": float(recall == 1),
        "completion_rr_at_3": reciprocal,
    }


def rank(chunks: list[dict], vectors: list[list[float]], query: list[float]) -> list[dict]:
    if len(chunks) != len(vectors):
        raise ValueError("Chunk/vector count differs")
    pairs = [(cosine(v, query), c) for c, v in zip(chunks, vectors, strict=True)]
    return [dict(c, similarity=s) for s, c in sorted(pairs, key=lambda p: (-p[0], p[1]["id"]))]
