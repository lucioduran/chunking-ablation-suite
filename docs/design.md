# Experimental design

Frozen before evaluation: 18 original fictional documents, 54 queries, six source
families. Aster and Birch are development (18 queries), Cobalt through Flint are
evaluation (36 queries). Documents and station identities are disjoint across
splits; templates are intentionally shared. This is author-known held-out data,
not blind or distribution-shift evaluation. All documents remain in the retrieval
index for both splits, as in retrieval over a fixed library. Only query selection
changes. No configuration is selected using evaluation results.

## Chunk boundaries

Documents consist of literal blocks with section IDs. Text is joined with two LF
characters. All chunks retain half-open character offsets into that source.
Fixed chunks use whitespace words, with 64 or 96 words and optional 16-word overlap.
Structure chunks merge adjacent blocks within a section up to the word budget.
Semantic chunks merge adjacent blocks when their MiniLM cosine similarity is at
least the threshold, also subject to the budget. Semantic boundaries are genuine
neural embedding decisions; section labels and query relevance are not inputs.
Code fences and tables are atomic for structure and semantic methods. A single
oversized block remains intact, so their budgets are soft. Fixed windows have hard
budgets. These different preservation policies are part of the method treatment,
not evidence that semantic decisions alone cause any observed difference.

MiniLM mean-pooled, attention-masked, L2-normalized vectors are used for both
boundary selection and retrieval. The model and revision are fixed in source.
Encoding allows at most 256 wordpiece tokens including special tokens and rejects
longer input instead of silently truncating. CPU inference uses two threads.

## One-variable-at-a-time contrasts

Eight configurations are declared in code. Compare fixed-64 with structure-64 and
semantic-64 for the method treatment. For each method compare 64 with 96 for size.
Compare fixed-64 with fixed-64-overlap16 for overlap. Compare semantic-64 with
semantic-64-threshold07 for threshold (0.5 versus 0.7). All other settings stay
fixed. This is not a factorial design and does not estimate interactions.

## Scoring

Rank every chunk in the complete library by cosine similarity, ties by chunk ID.
Use the same top-three cutoff for all configurations. Each query identifies one
source document and one or more minimal literal answer-evidence spans. A span is
recalled only if its full character interval is covered by the union of retrieved
chunks from that document. Whitespace gaps count as gaps. Evidence recall is the
fraction of spans covered. Complete@3 requires all spans. Completion reciprocal
rank is the reciprocal of the first prefix with complete evidence, or zero. It is
not conventional first-relevant-document MRR. Report macro averages by source kind
and overall. Multi-span cross references require both source and target evidence.

## Cost and repeatability

Report chunk count, embedded text UTF-8 bytes, dense float32 vector payload bytes
(384 dimensions times four bytes per chunk), and construction time by kind.
Payload is a theoretical uncompressed representation of the actual vector count,
not on-disk JSON size, resident memory, or a database storage measurement.
Construction timings include chunking and chunk embedding, plus amortized block
embedding time for semantic configurations only. Model loading and query encoding
are separate. Block embeddings are computed once, reused, and charged equally to
each semantic configuration. Retrieval timing includes Python cosine scoring and
sorting, excluding query encoding. Runs are sequential, one observation each,
with no latency confidence intervals or throughput claims. Warm caches and method
order can affect timings. No paid inference or GPU is used.

Stored vectors, chunks, rankings, inputs, and summaries permit standard-library
replay. Replay establishes internal consistency, not authentic inference or timing.
Hash provenance identifies exact bytes; it is not a signature. CI uses saved
vectors and does not download or execute neural models. Real inference is evidenced
by the local experiment, which records its environment and model file hashes.
