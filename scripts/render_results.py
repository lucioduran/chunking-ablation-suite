"""Render tables from the recorded evaluation; never change experiment evidence."""

import json
from pathlib import Path


def render(report: dict) -> str:
    env = report["environment"]
    lines = [
        "# Recorded local evaluation",
        "",
        f"Measured on {env['cpu']}, {env['platform']}, Python {env['python']}, two CPU threads.",
        f"UTC timestamp: {env['timestamp']}. Implementation commit: `{env['git_commit']}`.",
        f"Working tree dirty at measurement: `{str(env['git_dirty']).lower()}`.",
        "",
        "All 36 evaluation queries are scored without tuning after the development run.",
        "Each type contributes 12 queries. The same 18-document index is used throughout.",
        "",
        "## Retrieval quality",
        "",
        "Recall is mean evidence-span recall. Complete requires every span. Completion RR",
        "is reciprocal rank of the first complete prefix, not conventional MRR.",
        "",
        "| Configuration | Evidence recall@3 | Complete@3 | Completion RR@3 | Code complete | Table complete | Cross-reference complete |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for run in report["runs"]:
        s = run["summary"]
        o = s["overall"]
        values = [o["evidence_recall_at_3"], o["complete_at_3"], o["completion_rr_at_3"]]
        values.extend(s[k]["complete_at_3"] for k in ("code", "table", "cross_reference"))
        lines.append(f"| {run['config']['id']} | " + " | ".join(f"{v:.3f}" for v in values) + " |")
    lines += [
        "",
        "## Index cost by document type",
        "",
        "These costs cover all six source documents per type, including development documents.",
        "Float32 payload is calculated from actual vector count and dimension, excluding metadata.",
        "Construction includes chunk embedding and, for semantic methods, amortized block embedding.",
        "Single sequential timings are not load-test or cross-platform performance estimates.",
        "",
        "| Configuration | Type | Chunks | Text bytes | Float32 payload bytes | Construction seconds |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for run in report["runs"]:
        for kind, c in run["costs"].items():
            lines.append(
                f"| {run['config']['id']} | {kind} | {c['chunks']} | {c['text_utf8_bytes']} | "
                f"{c['vector_float32_bytes']} | {c['construction_seconds']:.3f} |"
            )
    lines += [
        "",
        "## One-variable contrasts",
        "",
        "Differences are variant minus baseline in Complete@3, in percentage points.",
        "",
        "| Variable | Baseline | Variant | Overall | Code | Table | Cross reference |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for contrast in report["contrasts"]:
        delta = contrast["complete_at_3_delta"]
        values = " | ".join(
            f"{100 * delta[k]:+.1f}" for k in ("overall", "code", "table", "cross_reference")
        )
        lines.append(
            f"| {contrast['variable']} | {contrast['baseline']} | {contrast['variant']} | {values} |"
        )
    lines += [
        "",
        "## Timing boundaries",
        "",
        f"Model load and hash verification: {env['model_load_seconds']:.3f} seconds.",
        f"Encoding all evaluation queries: {report['query_seconds']:.3f} seconds.",
        f"Shared block embedding pass: {sum(report['block_seconds'].values()):.3f} seconds.",
        "The block pass is charged to every semantic configuration as if constructed independently.",
        "All individual retrieval times and raw vectors remain in the report.",
        "",
        "## Interpretation",
        "",
        "Structure-96 obtains 33/36 complete queries, compared with 21/36 for fixed-64.",
        "Fixed-96 obtains 31/36 and adding 16-word overlap to fixed-64 obtains 32/36.",
        "Both semantic sizes obtain 12/36. These are observations on this fixture only.",
        "",
        "At budget 64, no adjacent block pair fits. Structure-64, semantic-64, and the",
        "0.7-threshold variant therefore have identical boundaries. Their threshold contrast",
        "does not test threshold sensitivity: the size constraint dominates every decision.",
        "At budget 96, 60 adjacent pairs fit, with measured cosine similarities from about",
        "0.301 to 0.750. Semantic decisions now change boundaries: semantic-96 has 68 chunks",
        "versus 84 for structure-96. Fewer chunks do not imply better evidence retrieval.",
        "",
        "Code blocks and tables lack station names inside the atomic content. Isolating them",
        "can rank another station's similar chunk above the target or prefer narrative context.",
        "Structure-96 combines their introductory context with the atomic content in the same",
        "section. This helps here, but also exposes the repeated-template nature of the fixture.",
        "",
        "Cross-reference queries benefit from separate, named source and target blocks.",
        "All structure and semantic configurations complete 12/12 cross-reference queries.",
        "This is evidence retrieval, not proof of link resolution or correct generated answers.",
        "",
        "The development and evaluation splits share templates. Semantic-96 completes 9/18",
        "development queries but only 12/36 evaluation queries. No configuration was adjusted",
        "to repair that outcome. No confidence intervals or statistical superiority are claimed.",
        "",
        "Rebuild these tables with `python scripts/render_results.py`. The full per-type",
        "evidence recall and completion RR are also available in `results/eval/summary.json`.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    report = json.loads(Path("results/eval/report.json").read_text(encoding="utf-8"))
    Path("docs/results.md").write_text(render(report), encoding="utf-8")
