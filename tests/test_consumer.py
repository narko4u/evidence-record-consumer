"""Tests for the evidence-record consumer.

The vector suite is the load-bearing test: it reproduces every published
canonical byte string and digest for both registered artifact types, and it
exercises every MUST-FAIL case for the reason the vector states. The remaining
tests pin the rules that matter independently of the vectors.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from evidence_record_consumer import (  # noqa: E402
    ConsumerError,
    appraisal_identifier,
    bind_appraisal_to_record,
    canonical_bytes,
    check_digest_form,
    digest,
    record_identifier,
    validate_record,
)
from evidence_record_consumer.vectors import run_vector_sets  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES = os.path.join(ROOT, "samples")
VECTOR_FILES = [
    os.path.join(ROOT, "vectors", "evidence-record-vectors-v0.1.json"),
    os.path.join(ROOT, "vectors", "evidence-appraisal-vectors-v0.1.json"),
]


def load(name):
    with open(os.path.join(SAMPLES, name), "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_published_vectors_all_pass():
    results = run_vector_sets(VECTOR_FILES, SAMPLES)
    failures = [result for result in results if not result["ok"]]
    assert failures == [], failures
    assert len(results) == 20
    positives = [result for result in results if result["kind"] == "positive"]
    negatives = [result for result in results if result["kind"] == "negative"]
    assert len(positives) == 8
    assert len(negatives) == 12


def test_identifier_matches_the_pinned_digest_for_the_e4_sample():
    result = record_identifier(load("er-00003-e4-operationally-conformant.json"))
    assert result["digest"] == (
        "c65a52c39246a73f58f4d185b104ba1c1237e25198c5b5deeab1de77e80232a1"
    )


def test_appraisal_binds_to_its_subject_record():
    appraisal = load("ea-00001-e4-agreement.json")
    record = load("er-00003-e4-operationally-conformant.json")
    binding = bind_appraisal_to_record(appraisal, record)
    assert binding["bound"] == "true"
    assert binding["record_id"] == "er-00003"


def test_wrong_pairing_is_rejected():
    appraisal = load("ea-00003-e3-contradiction.json")
    record = load("er-00003-e4-operationally-conformant.json")
    with pytest.raises(ConsumerError) as excinfo:
        bind_appraisal_to_record(appraisal, record)
    assert "does not match the identifier derived from the record bytes" in str(
        excinfo.value
    )


def test_producer_grade_stamp_is_rejected():
    record = load("er-00003-e4-operationally-conformant.json")
    record["e_grade"] = "E4"
    with pytest.raises(ConsumerError) as excinfo:
        validate_record(record)
    assert "additionalProperties: e_grade" in str(excinfo.value)


def test_unregistered_grade_is_rejected_not_tolerated():
    record = load("er-00003-e4-operationally-conformant.json")
    record["grade"] = "E5"
    with pytest.raises(ConsumerError) as excinfo:
        validate_record(record)
    assert "grade not in [E0, E1, E2, E3, E4]" in str(excinfo.value)


def test_prefixed_and_uppercase_digest_forms_are_rejected_without_repair():
    bare = "c65a52c39246a73f58f4d185b104ba1c1237e25198c5b5deeab1de77e80232a1"
    assert check_digest_form(bare) == bare
    with pytest.raises(ConsumerError):
        check_digest_form("sha256:" + bare)
    with pytest.raises(ConsumerError):
        check_digest_form(bare.upper())


def test_derived_observation_requires_provenance():
    record = load("er-00005-e3-derived-reconstructed.json")
    validate_record(record)
    record["provenance"] = []
    with pytest.raises(ConsumerError) as excinfo:
        validate_record(record)
    assert "requires provenance" in str(excinfo.value)


def test_numbers_are_refused_rather_than_serialized():
    with pytest.raises(ConsumerError):
        canonical_bytes({"confidence": 0.95})


def test_member_names_sort_by_utf16_code_units():
    """RFC 8785 section 3.2.3 sorts by UTF-16 code units, not by code point.
    U+1F600 encodes as the surrogate pair D83D DE00, which sorts before U+FF21,
    while code point order would put it after."""
    canonical = canonical_bytes({"\uff21": "bmp", "\U0001f600": "non-bmp"}).decode()
    assert canonical == '{"\U0001f600":"non-bmp","\uff21":"bmp"}'


def test_missing_required_member_is_rejected():
    record = load("er-00003-e4-operationally-conformant.json")
    del record["integrity"]
    with pytest.raises(ConsumerError) as excinfo:
        validate_record(record)
    assert "missing required member evidence-record.integrity" in str(excinfo.value)


def test_appraisal_identifier_matches_the_pinned_digest():
    result = appraisal_identifier(load("ea-00001-e4-agreement.json"))
    assert result["digest"] == (
        "916265d4e0b36453ff809042385b571dd785cc56025366fbe53823a951dc030a"
    )
    assert digest(load("ea-00001-e4-agreement.json")) == result["digest"]
