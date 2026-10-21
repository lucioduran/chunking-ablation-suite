# Fixture and command contract

The UTF-8 JSON root contains exactly `version` (1), `documents`, and `queries`.
Documents have unique nonempty string `id`, `kind` (`code`, `table`, or
`cross_reference`), `split` (`dev` or `eval`), and nonempty `blocks`.
Each block contains nonempty string `section` and `text` fields. A block is atomic
for structure and semantic chunkers. The loader does not parse Markdown; authors
must put a complete code fence or table in one block to preserve it.

A query has unique nonempty string `id`, `doc_id`, `split`, nonempty `text`, and a
nonempty `evidence` list. Its split must equal its source document's split.
Each evidence entry is a two-integer half-open character interval `[start, end]`
inside the document text formed by joining blocks with exactly two LF characters.
Offsets count Python Unicode characters, not UTF-8 bytes or tokenizer tokens.
Extra object fields, duplicate IDs, invalid kinds, missing documents, invalid
ranges, empty strings, and split inconsistencies are rejected.

All documents are indexed for each run, including documents whose query split is
not selected. Labels and split names never enter embedding text or chunk selection.
The matrix is intentionally fixed in `core.configurations`; new experiments should
version that matrix and keep the old reports rather than tune the evaluation data.

The standard-library evaluator accepts finite, nonzero vectors of matching size.
The production encoder emits 384-dimensional vectors. Snapshot-file hashes prevent
accidentally running a different local model under the same revision label.

A report embeds raw vectors and the exact chunk text. Verification regenerates
chunks and checks every saved ranking, query score, group summary, index count,
text byte count, vector payload count, and one-variable contrast. Timing and
hardware metadata are observations and cannot be independently reconstructed.
`summary.json` is a convenience export; the verifier's authority is `report.json`
plus the independently supplied fixture file, not that export.
