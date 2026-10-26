"""Command-line interface for the offline buyer research module."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .core import rank_buyers, validate_records

_DEFAULT_DATA = Path(__file__).parent / "data" / "sample_buyers.json"


def _load_records(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open(encoding="utf-8") as data_file:
            records = json.load(data_file)
    except OSError as error:
        raise ValueError(f"cannot read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in {path}: {error}") from error

    errors = validate_records(records)
    if errors:
        raise ValueError("invalid buyer data:\n" + "\n".join(f"- {error}" for error in errors))
    return records


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="buyer-intel",
        description="Rank manually researched business prospects using documented evidence.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help="validate a buyer JSON file")
    validate.add_argument("--input", type=Path, default=_DEFAULT_DATA)

    rank = commands.add_parser("rank", help="rank buyers for a product")
    rank.add_argument("--input", type=Path, default=_DEFAULT_DATA)
    rank.add_argument("--product", required=True, help="product label to match exactly")
    rank.add_argument("--json", action="store_true", help="print machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        records = _load_records(args.input)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2

    if args.command == "validate":
        print(f"Validated {len(records)} buyer record(s): {args.input}")
        return 0

    ranked = rank_buyers(records, args.product)
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "company": buyer.company,
                        "country": buyer.country,
                        "score": buyer.score,
                        "reasons": list(buyer.reasons),
                        "public_business_email": buyer.public_business_email,
                    }
                    for buyer in ranked
                ],
                indent=2,
            )
        )
        return 0

    print(f"Buyer ranking for: {args.product}")
    print("-" * 72)
    for buyer in ranked:
        print(f"{buyer.score:3}  {buyer.company} ({buyer.country})")
        print(f"     Evidence: {', '.join(buyer.reasons)}")
        if buyer.public_business_email:
            print(f"     Public business email: {buyer.public_business_email}")
    print("\nScores prioritize recorded evidence; they do not confirm buyer quality.")
    return 0
