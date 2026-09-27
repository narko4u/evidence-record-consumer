"""Command line for the evidence-record consumer."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from .consumer import (
    ConsumerError,
    appraisal_identifier,
    bind_appraisal_to_record,
    record_identifier,
)
from .vectors import format_results, run_vector_sets


def _read_json(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _cmd_record(args: argparse.Namespace) -> int:
    try:
        result = record_identifier(_read_json(args.path))
    except (ConsumerError, OSError, ValueError) as exc:
        print("REJECT evidence-record: %s" % exc)
        return 1
    print("ACCEPT evidence-record")
    print("  derived identifier (%s, %s): %s" % (
        result["canonicalization"], result["representation"], result["digest"]))
    return 0


def _cmd_appraisal(args: argparse.Namespace) -> int:
    try:
        appraisal = _read_json(args.path)
        result = appraisal_identifier(appraisal)
    except (ConsumerError, OSError, ValueError) as exc:
        print("REJECT evidence-appraisal: %s" % exc)
        return 1
    print("ACCEPT evidence-appraisal")
    print("  derived identifier (%s, %s): %s" % (
        result["canonicalization"], result["representation"], result["digest"]))
    if args.record:
        try:
            binding = bind_appraisal_to_record(appraisal, _read_json(args.record))
        except (ConsumerError, OSError, ValueError) as exc:
            print("REJECT binding: %s" % exc)
            return 1
        print(
            "  bound to %s at %s (subject digest re-derived from the record bytes)"
            % (binding["record_id"], binding["derived_digest"])
        )
    return 0


def _cmd_vectors(args: argparse.Namespace) -> int:
    samples = args.samples
    if not os.path.isdir(samples):
        print("samples directory not found: %s" % samples)
        return 2
    results = run_vector_sets(args.vectors, samples)
    return format_results(results)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evidence-record-consumer",
        description=(
            "Consume the registered evidence-record and evidence-appraisal "
            "artifact types: derive their identifiers from the registered "
            "context, and reject anything outside the closed vocabularies."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    record = sub.add_parser("record", help="derive the identifier of an evidence record")
    record.add_argument("path", help="path to an evidence record JSON file")
    record.set_defaults(func=_cmd_record)

    appraisal = sub.add_parser(
        "appraisal", help="derive the identifier of an appraisal, optionally binding it"
    )
    appraisal.add_argument("path", help="path to an evidence appraisal JSON file")
    appraisal.add_argument(
        "--record",
        help="path to the record the appraisal cites, to verify the typed-digest binding",
    )
    appraisal.set_defaults(func=_cmd_appraisal)

    vectors = sub.add_parser(
        "vectors", help="reproduce the published conflict-free vector sets"
    )
    vectors.add_argument("vectors", nargs="+", help="one or more vector JSON files")
    vectors.add_argument(
        "--samples",
        default="samples",
        help="directory holding the vendored sample artifacts (default: samples)",
    )
    vectors.set_defaults(func=_cmd_vectors)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
