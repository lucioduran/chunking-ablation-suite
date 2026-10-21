"""Run, summarize, and replay the frozen experiment."""

import importlib.metadata
import json
import platform
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from .core import (
    MODEL_ID,
    MODEL_REVISION,
    chunk,
    configurations,
    cosine,
    digest,
    load_data,
    rank,
    score,
)
from .model import Encoder


def summarize(rows: list[dict]) -> dict:
    groups = {"overall": rows}
    groups.update(
        {kind: [r for r in rows if r["kind"] == kind] for kind in sorted({r["kind"] for r in rows})}
    )
    return {
        kind: {
            "queries": len(items),
            **{
                key: sum(r["metrics"][key] for r in items) / len(items)
                for key in ("evidence_recall_at_3", "complete_at_3", "completion_rr_at_3")
            },
        }
        for kind, items in groups.items()
        if items
    }


def contrasts(summaries: dict) -> list[dict]:
    pairs = [("fixed-64", "structure-64", "method"), ("fixed-64", "semantic-64", "method")]
    pairs.extend(
        (f"{method}-64", f"{method}-96", "size") for method in ("fixed", "structure", "semantic")
    )
    pairs.extend(
        [
            ("fixed-64", "fixed-64-overlap16", "overlap"),
            ("semantic-64", "semantic-64-threshold07", "threshold"),
        ]
    )
    return [
        {
            "baseline": a,
            "variant": b,
            "variable": variable,
            "complete_at_3_delta": {
                kind: summaries[b][kind]["complete_at_3"] - summaries[a][kind]["complete_at_3"]
                for kind in summaries[a]
            },
        }
        for a, b, variable in pairs
    ]


def environment() -> dict:
    cpu = platform.processor()
    if sys.platform == "darwin":
        cpu = subprocess.check_output(
            ["sysctl", "-n", "machdep.cpu.brand_string"], text=True
        ).strip()
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu": cpu,
        "threads": 2,
        "device": "cpu",
        "timestamp": datetime.now(UTC).isoformat(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("torch", "transformers", "numpy", "huggingface-hub", "safetensors")
        },
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], text=True)),
    }


def cost(chunks: list[dict], dimensions: int) -> dict:
    return {
        "chunks": len(chunks),
        "text_utf8_bytes": sum(len(c["text"].encode()) for c in chunks),
        "vector_float32_bytes": len(chunks) * dimensions * 4,
    }


def evaluate(data: dict, split: str, encoder, metadata: dict) -> dict:
    queries = [q for q in data["queries"] if q["split"] == split]
    if not queries:
        raise ValueError("No queries in split")
    docs = data["documents"]
    blocks, block_times = {}, {}
    for doc in docs:
        start = time.perf_counter()
        blocks[doc["id"]] = encoder.encode([b["text"] for b in doc["blocks"]])
        block_times[doc["id"]] = time.perf_counter() - start
    start = time.perf_counter()
    query_vectors = encoder.encode([q["text"] for q in queries])
    query_seconds = time.perf_counter() - start
    runs = []
    for config in configurations():
        chunks, vectors, costs = [], [], {}
        for doc in docs:
            start = time.perf_counter()
            current = chunk(doc, config, blocks[doc["id"]])
            embedded = encoder.encode([c["text"] for c in current])
            elapsed = time.perf_counter() - start
            if config["method"] == "semantic":
                elapsed += block_times[doc["id"]]
            chunks.extend(current)
            vectors.extend(embedded)
            entry = costs.setdefault(doc["kind"], {"construction_seconds": 0.0})
            entry["construction_seconds"] += elapsed
        for kind, entry in costs.items():
            subset = [c for c in chunks if c["kind"] == kind]
            entry.update(cost(subset, len(vectors[0])))
            entry["over_budget_chunks"] = sum(
                len(c["text"].split()) > config["size"] for c in subset
            )
        rows = []
        for q, vector in zip(queries, query_vectors, strict=True):
            start = time.perf_counter()
            ranking = rank(chunks, vectors, vector)[:3]
            elapsed = time.perf_counter() - start
            kind = next(d["kind"] for d in docs if d["id"] == q["doc_id"])
            rows.append(
                {
                    "query_id": q["id"],
                    "kind": kind,
                    "retrieval_seconds": elapsed,
                    "ranking": [{"id": c["id"], "similarity": c["similarity"]} for c in ranking],
                    "metrics": score(q, ranking),
                }
            )
        runs.append(
            {
                "config": config,
                "chunks": chunks,
                "vectors": vectors,
                "costs": costs,
                "rows": rows,
                "summary": summarize(rows),
            }
        )
    summaries = {r["config"]["id"]: r["summary"] for r in runs}
    return {
        "schema_version": 1,
        "data_hash": digest(data),
        "split": split,
        "model": {"id": MODEL_ID, "revision": MODEL_REVISION},
        "environment": metadata,
        "block_vectors": blocks,
        "block_seconds": block_times,
        "query_vectors": query_vectors,
        "query_seconds": query_seconds,
        "runs": runs,
        "contrasts": contrasts(summaries),
    }


def verify(report: dict, data: dict) -> dict:
    if (
        report["schema_version"] != 1
        or report["data_hash"] != digest(data)
        or report["model"] != {"id": MODEL_ID, "revision": MODEL_REVISION}
        or report["split"] not in {"dev", "eval"}
    ):
        raise ValueError("Report provenance mismatch")
    queries = [q for q in data["queries"] if q["split"] == report["split"]]
    qv = report["query_vectors"]
    if len(qv) != len(queries) or not queries:
        raise ValueError("Query count mismatch")
    runs = report["runs"]
    if [r["config"] for r in runs] != configurations():
        raise ValueError("Configuration matrix differs")
    for doc in data["documents"]:
        vectors = report["block_vectors"][doc["id"]]
        if len(vectors) != len(doc["blocks"]):
            raise ValueError("Block vector count mismatch")
        for v in vectors:
            cosine(v, v)
    for run in runs:
        expected = [
            c
            for doc in data["documents"]
            for c in chunk(doc, run["config"], report["block_vectors"][doc["id"]])
        ]
        if expected != run["chunks"] or len(run["rows"]) != len(queries):
            raise ValueError("Chunk reconstruction or query count differs")
        for q, v, row in zip(queries, qv, run["rows"], strict=True):
            ranking = rank(expected, run["vectors"], v)[:3]
            kind = next(d["kind"] for d in data["documents"] if d["id"] == q["doc_id"])
            if (
                row["query_id"] != q["id"]
                or row["kind"] != kind
                or row["ranking"]
                != [{"id": c["id"], "similarity": c["similarity"]} for c in ranking]
                or row["metrics"] != score(q, ranking)
            ):
                raise ValueError("Ranking or scoring differs")
        if set(run["costs"]) != {c["kind"] for c in expected}:
            raise ValueError("Cost groups differ")
        for kind, entry in run["costs"].items():
            subset = [c for c in expected if c["kind"] == kind]
            expected_cost = cost(subset, len(run["vectors"][0]))
            expected_cost["over_budget_chunks"] = sum(
                len(c["text"].split()) > run["config"]["size"] for c in subset
            )
            if any(entry[key] != value for key, value in expected_cost.items()):
                raise ValueError("Index cost differs")
        if run["summary"] != summarize(run["rows"]):
            raise ValueError("Summary differs")
    if report["contrasts"] != contrasts({r["config"]["id"]: r["summary"] for r in runs}):
        raise ValueError("Contrasts differ")
    return {
        "verified": True,
        "split": report["split"],
        "configurations": len(runs),
        "queries": len(queries),
    }


def run(data_path: Path, model_path: Path, output: Path, split: str) -> dict:
    data = load_data(data_path)
    output.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    encoder = Encoder(model_path)
    metadata = environment()
    metadata["model_load_seconds"] = time.perf_counter() - start
    metadata["model_files_sha256"] = encoder.hashes
    report = evaluate(data, split, encoder, metadata)
    verify(report, data)
    (output / "report.json").write_text(
        json.dumps(report, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    summary = {
        "split": split,
        "summaries": {r["config"]["id"]: r["summary"] for r in report["runs"]},
        "costs": {r["config"]["id"]: r["costs"] for r in report["runs"]},
        "contrasts": report["contrasts"],
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary
