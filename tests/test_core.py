import copy
import json
import tempfile
import unittest
from pathlib import Path

from chunking_suite.core import (
    block_spans,
    chunk,
    configurations,
    cosine,
    covered,
    document_text,
    load_data,
    rank,
    score,
)
from scripts.create_fixtures import create


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.doc = {
            "id": "d",
            "kind": "code",
            "split": "dev",
            "blocks": [
                {"section": "a", "text": "one two"},
                {"section": "a", "text": "three four"},
                {"section": "b", "text": "five six"},
            ],
        }
        self.config = {"method": "fixed", "size": 3, "overlap": 0, "threshold": 0.5}
        self.vectors = [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]]

    def test_fixture_generation_and_split(self):
        actual = load_data(Path("data/fixtures.json"))
        self.assertEqual(actual, create())
        self.assertEqual(len(actual["documents"]), 18)
        self.assertEqual(len(actual["queries"]), 54)
        for q in actual["queries"]:
            text = document_text(next(d for d in actual["documents"] if d["id"] == q["doc_id"]))
            self.assertTrue(all(text[a:b].strip() for a, b in q["evidence"]))

    def test_invalid_data(self):
        mutations = [
            lambda d: d.update(version=3),
            lambda d: d.update(documents=[]),
            lambda d: d.update(extra=1),
            lambda d: d["documents"].append(d["documents"][0]),
            lambda d: d["documents"][0].update(kind="unknown"),
            lambda d: d["documents"][0].update(split="train"),
            lambda d: d["documents"][0]["blocks"][0].update(text=" "),
            lambda d: d["queries"].append(d["queries"][0]),
            lambda d: d["queries"][0].update(doc_id="absent"),
            lambda d: d["queries"][0].update(split="eval"),
            lambda d: d["queries"][0].update(text=""),
            lambda d: d["queries"][0].update(evidence=[]),
            lambda d: d["queries"][0].update(evidence=[[0, 100000]]),
            lambda d: d["queries"][0].update(evidence=[[True, 1]]),
            lambda d: d["queries"][0].update(evidence=[[4, 3]]),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            for change in mutations:
                with self.subTest(change=change):
                    data = create()
                    change(data)
                    path.write_text(json.dumps(data), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_data(path)

    def test_fixed_offsets_and_overlap(self):
        result = chunk(self.doc, self.config, [])
        self.assertEqual([c["text"] for c in result], ["one two\n\nthree ", "four\n\nfive six"])
        self.config["overlap"] = 1
        result = chunk(self.doc, self.config, [])
        self.assertEqual(
            [c["text"] for c in result], ["one two\n\nthree ", "three four\n\nfive ", "five six"]
        )
        text = document_text(self.doc)
        self.assertTrue(all(text[c["start"] : c["end"]] == c["text"] for c in result))
        self.assertEqual(block_spans(self.doc), [(0, 7), (9, 19), (21, 29)])

    def test_structure_and_semantic_decisions(self):
        config = dict(self.config, method="structure", size=10)
        self.assertEqual(len(chunk(self.doc, config, [])), 2)
        config["method"] = "semantic"
        result = chunk(self.doc, config, self.vectors)
        self.assertEqual(len(result), 2)
        config["threshold"] = 0
        self.assertEqual(len(chunk(self.doc, config, self.vectors)), 1)
        config["size"] = 1
        self.assertEqual(len(chunk(self.doc, config, self.vectors)), 3)
        self.assertEqual(chunk(self.doc, config, self.vectors)[0]["text"], "one two")

    def test_chunk_failures(self):
        for update in (
            {"method": "bad"},
            {"size": 0},
            {"size": True},
            {"overlap": 3},
            {"method": "structure", "overlap": 1},
            {"threshold": 2},
        ):
            with self.assertRaises(ValueError):
                chunk(self.doc, dict(self.config, **update), [])
        with self.assertRaises(ValueError):
            chunk(self.doc, dict(self.config, method="semantic"), [])
        empty = copy.deepcopy(self.doc)
        empty["blocks"][0]["text"] = " "
        empty["blocks"] = empty["blocks"][:1]
        with self.assertRaises(ValueError):
            chunk(empty, self.config, [])

    def test_cosine_and_ranking(self):
        self.assertAlmostEqual(cosine([1, 1], [1, 0]), 2**-0.5)
        for a, b in (([], []), ([0], [1]), ([1], [1, 2]), ([float("nan")], [1])):
            with self.assertRaises(ValueError):
                cosine(a, b)
        chunks = [{"id": "b"}, {"id": "a"}]
        self.assertEqual([r["id"] for r in rank(chunks, [[1], [1]], [1])], ["a", "b"])
        with self.assertRaises(ValueError):
            rank(chunks, [[1]], [1])

    def test_evidence_union_and_completion(self):
        self.assertTrue(covered([2, 7], [(0, 4), (4, 8)]))
        self.assertFalse(covered([2, 7], [(0, 4), (5, 8)]))
        self.assertFalse(covered([2, 7], [(3, 8)]))
        q = {"doc_id": "d", "evidence": [[0, 4], [8, 12]]}
        ranking = [
            {"doc_id": "wrong", "start": 0, "end": 12},
            {"doc_id": "d", "start": 0, "end": 4},
            {"doc_id": "d", "start": 8, "end": 12},
        ]
        self.assertEqual(
            score(q, ranking),
            {"evidence_recall_at_3": 1, "complete_at_3": 1, "completion_rr_at_3": 1 / 3},
        )
        self.assertEqual(score(q, ranking[:2])["evidence_recall_at_3"], 0.5)
        self.assertEqual(score(q, [])["complete_at_3"], 0)
        with self.assertRaises(ValueError):
            score(q, ranking, 0)

    def test_ovaat(self):
        configs = {c["id"]: c for c in configurations()}
        self.assertEqual(len(configs), 8)
        for a, b, key in [
            ("fixed-64", "fixed-64-overlap16", "overlap"),
            ("semantic-64", "semantic-64-threshold07", "threshold"),
        ]:
            self.assertEqual({k for k in configs[a] if configs[a][k] != configs[b][k]}, {"id", key})
