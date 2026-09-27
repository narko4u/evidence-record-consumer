"""Run the publisher's own published conflict-free vector sets against this
consumer.

The vectors are the owner's published set for the two registered artifact types,
vendored here at a pinned commit (see PROVENANCE.md). Running them is the whole
point of this repository: an implementation that is not the specification can
still reproduce every pinned canonical byte and digest, and must reject every
MUST-FAIL case for the reason the vector states rather than for one of its own.

Positives must reproduce the published canonical bytes and digest exactly.
Negatives must be rejected, and where the vector states a reason the rejection
message must carry the same reason, so a passing run is not a coincidence.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from .consumer import (
    ConsumerError,
    check_digest_form,
    digest,
    validate_appraisal,
    validate_record,
)
from .jcs import canonical_bytes

__all__ = ["run_vector_file", "run_vector_sets", "format_results"]


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _sample_path(samples_dir: str, declared: str) -> str:
    """Vectors declare inputs relative to the specification repository. Resolve
    to the vendored copy by file name."""
    return os.path.join(samples_dir, os.path.basename(declared))


def _expected_token(expected: str) -> Optional[str]:
    """Pull the stated reason out of an `expected` clause such as
    'REJECT (grade not in [E0, E1, E2, E3, E4])'."""
    if not isinstance(expected, str):
        return None
    match = re.search(r"\(([^()]+)\)\s*$", expected.strip())
    if not match:
        return None
    token = match.group(1).strip()
    return token or None


def _mutated(value: Any, mutation: str) -> Any:
    """Apply the single-byte mutation a mutation probe describes."""
    match = re.search(r"flip the (\w+) first character", mutation)
    if not match:
        raise ValueError("unrecognised mutation instruction: %r" % mutation)
    field = match.group(1)
    clone = json.loads(json.dumps(value))
    original = clone[field]
    first = original[0]
    clone[field] = ("b" if first != "b" else "c") + original[1:]
    return clone


def _reject_reason(callable_) -> Optional[str]:
    """Return the rejection reason, or None if the call did not reject."""
    try:
        callable_()
    except ConsumerError as exc:
        return str(exc)
    return None


def run_vector_file(
    vectors_path: str, samples_dir: str, base_dir: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Run one published vector file. Returns one result dict per vector."""
    document = _read_json(vectors_path)
    artifact_type = document.get("artifact_type")
    results: List[Dict[str, Any]] = []
    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(vectors_path)) or "."

    validate = validate_appraisal if artifact_type == "evidence-appraisal" else validate_record

    kat_digests: Dict[str, str] = {}
    for vector in document.get("positive", []):
        kat_digests[vector["id"]] = vector.get("expected_digest_bare_hex", "")

    for vector in document.get("positive", []):
        identifier = vector["id"]
        detail: List[str] = []
        ok = True
        try:
            artifact = _read_json(_sample_path(samples_dir, vector["input_file"]))
            validate(artifact)
            produced_hex = canonical_bytes(artifact).hex()
            produced_digest = digest(artifact)
        except (ConsumerError, KeyError, ValueError, OSError) as exc:
            results.append(
                {
                    "id": identifier,
                    "kind": "positive",
                    "ok": False,
                    "detail": "could not reproduce: %s" % exc,
                }
            )
            continue

        expected_hex = vector.get("canonical_bytes_hex")
        if expected_hex is not None:
            if produced_hex == expected_hex:
                detail.append("canonical bytes match (%d bytes)" % (len(produced_hex) // 2))
            else:
                ok = False
                detail.append("canonical bytes DIFFER from the published bytes")
        expected_digest = vector.get("expected_digest_bare_hex")
        if expected_digest is not None:
            if produced_digest == expected_digest:
                detail.append("digest matches %s" % produced_digest[:16])
            else:
                ok = False
                detail.append(
                    "digest DIFFERS: produced %s, published %s"
                    % (produced_digest, expected_digest)
                )
        results.append(
            {
                "id": identifier,
                "kind": "positive",
                "ok": ok,
                "detail": "; ".join(detail),
            }
        )

    for vector in document.get("negative", []):
        identifier = vector["id"]
        expected = vector.get("expected", "")
        token = _expected_token(expected)

        if identifier == "ea-fail-01-grade-in-producer-record":
            # No input artifact is published for this one, so the runner builds
            # the artifact the rule is about: a valid record carrying a producer
            # grade stamp. The rule is that the grade belongs to the appraisal.
            probe = _read_json(_sample_path(samples_dir, "samples/er-00003-e4-operationally-conformant.json"))
            probe["e_grade"] = "E4"
            reason = _reject_reason(lambda: validate_record(probe))
            ok = reason is not None and "additionalProperties: e_grade" in reason
            results.append(
                {
                    "id": identifier,
                    "kind": "negative",
                    "ok": ok,
                    "detail": reason or "NOT REJECTED (a producer record stamped its own grade)",
                }
            )
            continue

        if identifier == "er-fail-05-representation-confusion":
            bare = check_digest_form(vector["bare_form_of_kat03"])
            reason = _reject_reason(
                lambda: check_digest_form(vector["prefixed_form_of_kat03"])
            )
            ok = (
                bare == vector["bare_form_of_kat03"]
                and reason is not None
                and token is not None
                and token in reason
            )
            results.append(
                {
                    "id": identifier,
                    "kind": "negative",
                    "ok": ok,
                    "detail": "bare form accepted, prefixed form rejected: %s"
                    % (reason or "NOT REJECTED"),
                }
            )
            continue

        if identifier == "er-fail-06-uppercase-hex":
            reason = _reject_reason(lambda: check_digest_form(vector["input_digest"]))
            ok = reason is not None and (
                token is None or token.replace("fails ", "") in reason or token in reason
            )
            results.append(
                {
                    "id": identifier,
                    "kind": "negative",
                    "ok": ok,
                    "detail": reason or "NOT REJECTED (uppercase hex accepted)",
                }
            )
            continue

        if "mutation" in vector:
            artifact = _read_json(_sample_path(samples_dir, vector["input_file"]))
            reference, _, field = vector["must_not_equal"].partition(".")
            mutated = _mutated(artifact, vector["mutation"])
            validate(mutated)
            produced = digest(mutated)
            published = kat_digests.get(reference)
            if published is None:
                published = next(
                    (
                        item.get("expected_digest_bare_hex")
                        for item in document.get("positive", [])
                        if item["id"] == reference
                    ),
                    None,
                )
            ok = published is not None and produced != published
            results.append(
                {
                    "id": identifier,
                    "kind": "negative",
                    "ok": ok,
                    "detail": "mutated digest %s differs from the pinned %s"
                    % (produced[:16], (published or "?")[:16]),
                }
            )
            continue

        if "input" in vector:
            artifact = vector["input"]
            reason = _reject_reason(lambda: validate(artifact))
            ok = reason is not None and (token is None or token in reason)
            results.append(
                {
                    "id": identifier,
                    "kind": "negative",
                    "ok": ok,
                    "detail": "rejected: %s" % (reason or "NOT REJECTED"),
                }
            )
            continue

        results.append(
            {
                "id": identifier,
                "kind": "negative",
                "ok": False,
                "detail": "vector not exercised by this runner",
            }
        )

    return results


def run_vector_sets(paths: List[str], samples_dir: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for path in paths:
        results.extend(run_vector_file(path, samples_dir))
    return results


def format_results(results: List[Dict[str, Any]], stream=None) -> int:
    """Print a per-vector report and return an exit code."""
    import sys

    stream = stream or sys.stdout
    positives = [r for r in results if r["kind"] == "positive"]
    negatives = [r for r in results if r["kind"] == "negative"]
    failures = [r for r in results if not r["ok"]]
    for result in results:
        mark = "PASS" if result["ok"] else "FAIL"
        print("%s  %-46s %s" % (mark, result["id"], result["detail"]), file=stream)
    print(
        "vectors: %d positives reproduced, %d MUST-FAIL cases exercised, %d FAILED"
        % (len(positives), len(negatives), len(failures)),
        file=stream,
    )
    return 1 if failures else 0
