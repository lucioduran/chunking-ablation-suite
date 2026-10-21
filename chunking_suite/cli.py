"""Command line interface with explicit download, run, and replay steps."""

import argparse
import json
from pathlib import Path

from .core import load_data
from .experiment import run, verify
from .model import download


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("download")
    fetch.add_argument("--cache", type=Path, default=Path(".cache/models"))
    for name in ("run", "verify"):
        command = sub.add_parser(name)
        command.add_argument("--data", type=Path, default=Path("data/fixtures.json"))
        if name == "run":
            command.add_argument("--model-path", type=Path, required=True)
            command.add_argument("--split", choices=("dev", "eval"), required=True)
            command.add_argument("--output", type=Path, required=True)
        else:
            command.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "download":
            result = {"model_path": download(args.cache)}
        elif args.command == "run":
            result = run(args.data, args.model_path, args.output, args.split)
        else:
            result = verify(
                json.loads(args.report.read_text(encoding="utf-8")), load_data(args.data)
            )
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, ImportError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2
