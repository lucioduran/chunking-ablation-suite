import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


class RepositoryTests(unittest.TestCase):
    def test_readme_contract(self):
        headings = re.findall(r"^## (.+)$", Path("README.md").read_text(encoding="utf-8"), re.M)
        self.assertEqual(
            headings,
            [
                "Problem",
                "Scope",
                "Quick start",
                "Usage",
                "Architecture",
                "Reproduction",
                "Results",
                "Testing",
                "Limitations",
                "Contributing",
                "License",
            ],
        )

    def test_text_policy(self):
        paths = [Path("README.md"), Path("CONTRIBUTING.md"), Path("SECURITY.md")]
        for folder in ("chunking_suite", "tests", "data", "docs", "scripts", ".github"):
            paths.extend(
                p for p in Path(folder).rglob("*") if p.suffix in {".py", ".md", ".json", ".yml"}
            )
        for path in paths:
            with self.subTest(path=str(path)):
                self.assertNotIn(chr(0x2014), path.read_text(encoding="utf-8"))

    def test_module_entrypoint(self):
        result = subprocess.run(
            [sys.executable, "-m", "chunking_suite", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("verify", result.stdout)

    def test_published_exports_match_reports(self):
        from scripts.render_results import render

        for split in ("dev", "eval"):
            report = json.loads(Path(f"results/{split}/report.json").read_text(encoding="utf-8"))
            summary = json.loads(Path(f"results/{split}/summary.json").read_text(encoding="utf-8"))
            self.assertEqual(
                summary["summaries"], {r["config"]["id"]: r["summary"] for r in report["runs"]}
            )
            self.assertEqual(
                summary["costs"], {r["config"]["id"]: r["costs"] for r in report["runs"]}
            )
            self.assertEqual(summary["contrasts"], report["contrasts"])
            if split == "eval":
                self.assertEqual(
                    Path("docs/results.md").read_text(encoding="utf-8"), render(report)
                )
