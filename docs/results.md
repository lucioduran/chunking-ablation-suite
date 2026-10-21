# Recorded local evaluation

Measured on Intel(R) Xeon(R) W-3223 CPU @ 3.50GHz, macOS-26.7.1-x86_64-i386-64bit, Python 3.11.13, two CPU threads.
UTC timestamp: 2026-10-21T21:57:38.943953+00:00. Implementation commit: `5e1f27c2aba7624f181e4b1a172873b5180b8f53`.
Working tree dirty at measurement: `false`.

All 36 evaluation queries are scored without tuning after the development run.
Each type contributes 12 queries. The same 18-document index is used throughout.

## Retrieval quality

Recall is mean evidence-span recall. Complete requires every span. Completion RR
is reciprocal rank of the first complete prefix, not conventional MRR.

| Configuration | Evidence recall@3 | Complete@3 | Completion RR@3 | Code complete | Table complete | Cross-reference complete |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| fixed-64 | 0.708 | 0.583 | 0.338 | 0.833 | 0.333 | 0.583 |
| fixed-96 | 0.889 | 0.861 | 0.588 | 1.000 | 0.750 | 0.833 |
| structure-64 | 0.444 | 0.333 | 0.167 | 0.000 | 0.000 | 1.000 |
| structure-96 | 0.958 | 0.917 | 0.639 | 0.750 | 1.000 | 1.000 |
| semantic-64 | 0.444 | 0.333 | 0.167 | 0.000 | 0.000 | 1.000 |
| semantic-96 | 0.444 | 0.333 | 0.213 | 0.000 | 0.000 | 1.000 |
| fixed-64-overlap16 | 0.917 | 0.889 | 0.648 | 1.000 | 0.833 | 0.833 |
| semantic-64-threshold07 | 0.444 | 0.333 | 0.167 | 0.000 | 0.000 | 1.000 |

## Index cost by document type

These costs cover all six source documents per type, including development documents.
Float32 payload is calculated from actual vector count and dimension, excluding metadata.
Construction includes chunk embedding and, for semantic methods, amortized block embedding.
Single sequential timings are not load-test or cross-platform performance estimates.

| Configuration | Type | Chunks | Text bytes | Float32 payload bytes | Construction seconds |
| --- | --- | ---: | ---: | ---: | ---: |
| fixed-64 | code | 24 | 8559 | 36864 | 0.404 |
| fixed-64 | table | 24 | 8014 | 36864 | 0.319 |
| fixed-64 | cross_reference | 30 | 11109 | 46080 | 0.389 |
| fixed-96 | code | 18 | 8559 | 27648 | 0.452 |
| fixed-96 | table | 18 | 8014 | 27648 | 0.365 |
| fixed-96 | cross_reference | 18 | 11109 | 27648 | 0.364 |
| structure-64 | code | 30 | 8511 | 46080 | 0.290 |
| structure-64 | table | 30 | 7966 | 46080 | 0.288 |
| structure-64 | cross_reference | 36 | 11049 | 55296 | 0.383 |
| structure-96 | code | 24 | 8523 | 36864 | 0.448 |
| structure-96 | table | 24 | 7978 | 36864 | 0.476 |
| structure-96 | cross_reference | 36 | 11049 | 55296 | 0.390 |
| semantic-64 | code | 30 | 8511 | 46080 | 1.329 |
| semantic-64 | table | 30 | 7966 | 46080 | 0.572 |
| semantic-64 | cross_reference | 36 | 11049 | 55296 | 0.793 |
| semantic-96 | code | 18 | 8535 | 27648 | 1.427 |
| semantic-96 | table | 19 | 7988 | 29184 | 0.708 |
| semantic-96 | cross_reference | 31 | 11059 | 47616 | 1.055 |
| fixed-64-overlap16 | code | 24 | 10935 | 36864 | 0.624 |
| fixed-64-overlap16 | table | 30 | 10144 | 46080 | 0.437 |
| fixed-64-overlap16 | cross_reference | 36 | 14190 | 55296 | 0.704 |
| semantic-64-threshold07 | code | 30 | 8511 | 46080 | 1.345 |
| semantic-64-threshold07 | table | 30 | 7966 | 46080 | 0.580 |
| semantic-64-threshold07 | cross_reference | 36 | 11049 | 55296 | 0.798 |

## One-variable contrasts

Differences are variant minus baseline in Complete@3, in percentage points.

| Variable | Baseline | Variant | Overall | Code | Table | Cross reference |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| method | fixed-64 | structure-64 | -25.0 | -83.3 | -33.3 | +41.7 |
| method | fixed-64 | semantic-64 | -25.0 | -83.3 | -33.3 | +41.7 |
| size | fixed-64 | fixed-96 | +27.8 | +16.7 | +41.7 | +25.0 |
| size | structure-64 | structure-96 | +58.3 | +75.0 | +100.0 | +0.0 |
| size | semantic-64 | semantic-96 | +0.0 | +0.0 | +0.0 | +0.0 |
| overlap | fixed-64 | fixed-64-overlap16 | +30.6 | +16.7 | +50.0 | +25.0 |
| threshold | semantic-64 | semantic-64-threshold07 | +0.0 | +0.0 | +0.0 | +0.0 |

## Timing boundaries

Model load and hash verification: 2.305 seconds.
Encoding all evaluation queries: 0.137 seconds.
Shared block embedding pass: 1.700 seconds.
The block pass is charged to every semantic configuration as if constructed independently.
All individual retrieval times and raw vectors remain in the report.

## Interpretation

Structure-96 obtains 33/36 complete queries, compared with 21/36 for fixed-64.
Fixed-96 obtains 31/36 and adding 16-word overlap to fixed-64 obtains 32/36.
Both semantic sizes obtain 12/36. These are observations on this fixture only.

At budget 64, no adjacent block pair fits. Structure-64, semantic-64, and the
0.7-threshold variant therefore have identical boundaries. Their threshold contrast
does not test threshold sensitivity: the size constraint dominates every decision.
At budget 96, 60 adjacent pairs fit, with measured cosine similarities from about
0.301 to 0.750. Semantic decisions now change boundaries: semantic-96 has 68 chunks
versus 84 for structure-96. Fewer chunks do not imply better evidence retrieval.

Code blocks and tables lack station names inside the atomic content. Isolating them
can rank another station's similar chunk above the target or prefer narrative context.
Structure-96 combines their introductory context with the atomic content in the same
section. This helps here, but also exposes the repeated-template nature of the fixture.

Cross-reference queries benefit from separate, named source and target blocks.
All structure and semantic configurations complete 12/12 cross-reference queries.
This is evidence retrieval, not proof of link resolution or correct generated answers.

The development and evaluation splits share templates. Semantic-96 completes 9/18
development queries but only 12/36 evaluation queries. No configuration was adjusted
to repair that outcome. No confidence intervals or statistical superiority are claimed.

Rebuild these tables with `python scripts/render_results.py`. The full per-type
evidence recall and completion RR are also available in `results/eval/summary.json`.
