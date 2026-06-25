"""Command-line entrypoint for the deterministic translator."""

from __future__ import annotations

import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gitbook-translator")
    parser.add_argument(
        "--dictionary-path",
        help="Directory containing target-language dictionaries.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
