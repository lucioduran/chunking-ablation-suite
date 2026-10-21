# Chunking Ablation Suite

[![CI](https://github.com/lucioduran/chunking-ablation-suite/actions/workflows/ci.yml/badge.svg)](https://github.com/lucioduran/chunking-ablation-suite/actions/workflows/ci.yml)

## Problem

Chunk boundaries can split a condition from its return value, separate table cells,
or omit the target of a cross reference. Finding the correct source document is
not enough. This suite measures whether the retrieved text contains complete
answer evidence and what each index costs to construct.

## Scope

Compare fixed windows, section-aware block packing, and neural semantic chunking
on 18 original fictional documents containing code, tables, and cross references.
Eight frozen configurations vary method, word budget, fixed-window overlap, and
semantic threshold one variable at a time. All use the same pinned MiniLM model,
CPU device, cosine retrieval, and top-three cutoff.

There are 18 development and 36 held-out evaluation queries. Source documents and
station identities are disjoint across splits; templates are shared. These small,
author-known fixtures are a reproducibility example, not a production benchmark.
No API key, paid inference, hosted model endpoint, or GPU is required.

## Quick start

Inspect and replay the recorded experiment using Python 3.11 and no dependencies:

```sh
git clone https://github.com/lucioduran/chunking-ablation-suite.git
cd chunking-ablation-suite
python -m unittest discover -v
python -m chunking_suite verify --report results/dev/report.json
python -m chunking_suite verify --report results/eval/report.json
```

Replay rebuilds chunk boundaries from saved block embeddings, recomputes rankings
from saved chunk/query vectors, and verifies evidence scores, costs, and contrasts.
It does not rerun neural inference or validate recorded wall-clock timings.

## Usage

| Command | Purpose |
| --- | --- |
| `download --cache PATH` | Download the exact public MiniLM snapshot and print its path |
| `run --model-path PATH --split dev --output PATH` | Construct all eight indexes and score development queries |
| `run --model-path PATH --split eval --output PATH` | Score the reserved evaluation queries |
| `verify --report PATH` | Replay a report with the standard library |

`run` and `verify` accept `--data PATH`, defaulting to `data/fixtures.json`.
Each run requires a new output directory. It writes `report.json` with vectors,
rankings, provenance, and measurements, plus a readable `summary.json`. A failed
run can leave an empty output directory; use another path for retrying. Exit code
0 means success and 2 means input, dependency, environment, or verification failure.
See [the data contract](docs/contract.md) for custom fixtures.

## Architecture

```text
literal blocks + evidence spans + frozen configuration matrix
                     |
        fixed / structure / MiniLM semantic boundaries
                     |
             source-offset chunks
                     |
          fixed MiniLM embeddings + cosine ranking
                     |
     top-three evidence coverage and per-type index costs
                     |
          raw report + summaries + offline replay
```

Semantic chunking uses adjacent block embedding similarity, not keywords or section
labels. Structure and semantic methods preserve atomic code and table blocks;
fixed windows may split them. Both block methods have a soft word budget when an
individual block is larger than the target. See [design and scoring](docs/design.md).

## Reproduction

The reference runtime is Python 3.11.13 on Intel macOS. Model inference uses two
CPU threads. The exact installed packages are in [requirements-local.lock](requirements-local.lock).
The lock is for that platform; other platforms may need compatible PyTorch wheels.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-local.lock
python -m chunking_suite download
```

Use the printed snapshot path as `MODEL_PATH` below:

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 python -m chunking_suite run --model-path MODEL_PATH --split dev --output build/reproduced-dev
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 python -m chunking_suite run --model-path MODEL_PATH --split eval --output build/reproduced-eval
python -m chunking_suite verify --report build/reproduced-eval/report.json
```

These are POSIX-shell examples. On Windows, activate `.venv\Scripts\Activate.ps1`
and set environment variables with `$env:NAME = 'VALUE'`. In the original shared
project workspace, both heavy runs were prefixed with the required
`python3 ../.coordination/benchmark_lock.py` wrapper to serialize benchmarks.
External reproductions should likewise avoid concurrent CPU-heavy work.

Model files are checked against committed SHA-256 values before loading. Inputs
above 256 tokenizer tokens fail instead of silently truncating. The adapter uses
attention-masked mean pooling and L2 normalization, following the
[pinned model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/blob/1110a243fdf4706b3f48f1d95db1a4f5529b4d41/README.md).
No tuning or fixture edits follow evaluation. Different platforms can change
floating-point rankings and timings; report those as new runs.

## Results

Actual local evaluation on Intel Xeon W-3223, two CPU threads, 36 held-out queries:

| Configuration | Complete evidence@3 | Chunks |
| --- | ---: | ---: |
| Fixed, 64 words | 21/36 | 78 |
| Fixed, 96 words | 31/36 | 54 |
| Structure, 64 words | 12/36 | 96 |
| Structure, 96 words | 33/36 | 84 |
| Semantic, 64 words | 12/36 | 96 |
| Semantic, 96 words | 12/36 | 68 |
| Fixed, 64 words, overlap 16 | 32/36 | 90 |
| Semantic, 64 words, threshold 0.7 | 12/36 | 96 |

The threshold ablation is null because no adjacent pair fits the 64-word budget.
At 96 words, neural boundaries change the index but do not improve complete
retrieval on evaluation queries. These outcomes do not establish a general winner.
Per-type quality, measured construction times, vector payload, and all contrasts
are recorded in [results analysis](docs/results.md).
Raw evidence is preserved in [development](results/dev/report.json) and
[evaluation](results/eval/report.json), with human-readable summaries alongside.

## Testing

```sh
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m ruff format --check .
python -m mypy chunking_suite
python -m coverage run -m unittest discover -v
python -m coverage report
```

Tests cover offset preservation, overlap, oversized atomic blocks, actual semantic
boundary decisions with controlled vectors, evidence union, cross-reference
completion, deterministic ties, malformed inputs, split leakage, tampered reports,
CLI errors, pinned downloads, and offline adapter contracts. CI runs these checks
and both recorded replays on Linux, macOS, and Windows. Adapter unit tests use
mocks; CI does not install model libraries. The local experiment supplies the real
inference evidence. Coverage must be at least 85% across statements and branches.

## Limitations

- Eighteen synthetic documents and repeated templates cannot establish a general
  winner. The held-out split is author-known and has no independent human review.
- Atomic-block preservation differs between methods. A method contrast includes
  that policy; it does not isolate the causal contribution of semantic embeddings.
- Word budgets differ from tokenizer budgets. Some semantic thresholds or size
  changes can yield identical chunks. Null ablations are reported as measured.
- Retrieval success means literal evidence coverage, not correct generated answers.
  No answer generation, factuality assessment, or unanswerable-query test is included.
- Cross references are scored, but there is no graph expansion or target following.
  Semantic chunking compares adjacent blocks only.
- Index payload excludes database metadata, compression, allocator overhead, and
  peak RAM. Timings are sequential observations on one host, without repeated runs,
  load tests, confidence intervals, or claims about concurrent production service.
- Replay checks internal consistency, not authenticity, model quality, or timing.
  The verifier shares implementation with the runner and expects trusted local files.
- The complete dataset and vectors reside in memory. This is a small research CLI,
  not a general Markdown parser or an untrusted upload service.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Preserve existing results, add tests for
behavior changes, and version new fixtures or experiments separately. Security
reporting guidance is in [SECURITY.md](SECURITY.md).

## License

Code, original fixtures, labels, documentation, and results use the [MIT license](LICENSE).
MiniLM is Apache-2.0 and is downloaded separately, not redistributed. Dependencies
retain their own licenses. See [model notices](docs/model-notices.md).
