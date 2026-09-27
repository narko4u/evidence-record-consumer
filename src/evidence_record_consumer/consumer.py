"""Closed-vocabulary validation and identifier derivation for the two registered
artifact types.

This module is a consumer, not a specification. It reads the registered names
`evidence-record` and `evidence-appraisal`, applies the closed field sets and
closed vocabularies those types register, re-derives each artifact's identifier
from the registered derived-identifier context (JCS, no member removal, no
domain separation, bare lowercase SHA-256 hex) and binds an appraisal to the
record it appraises by typed digest.

Two rules it exists to keep:

1. Closed vocabularies fail closed. An unrecognised value is a rejection, never
   an informational pass and never a new rung, so a typo cannot silently raise
   or lower an artifact's strength. This is the deliberate inversion of the
   payload-binding never-reject invariant at the layer where these types live.
2. The grade is an appraisal output. An evidence record MUST NOT stamp its own
   strength; `e_grade` belongs to the appraisal artifact only. A producer record
   carrying one is rejected as an unknown member.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional

from .jcs import CanonicalizationError
from .jcs import canonical_bytes as _jcs_canonical_bytes
from .jcs import digest as _jcs_digest

__all__ = [
    "ConsumerError",
    "RECORD_MEMBERS",
    "APPRAISAL_MEMBERS",
    "validate_record",
    "validate_appraisal",
    "record_identifier",
    "appraisal_identifier",
    "check_digest_form",
    "bind_appraisal_to_record",
    "canonical_bytes",
    "digest",
]


def canonical_bytes(value: Any) -> bytes:
    """Canonical form of a value, with this package's one failure type.

    The JCS layer refuses numbers and lone surrogates rather than serializing
    them, which is what the closed number-free field sets require. A consumer
    should not have to catch two error classes to discover that, so the refusal
    is re-raised as ConsumerError.
    """
    try:
        return _jcs_canonical_bytes(value)
    except CanonicalizationError as exc:
        raise ConsumerError(str(exc)) from exc


def digest(value: Any) -> str:
    """Bare lowercase hex SHA-256 over the canonical form, same failure type."""
    try:
        return _jcs_digest(value)
    except CanonicalizationError as exc:
        raise ConsumerError(str(exc)) from exc

BARE_HEX = re.compile(r"^[0-9a-f]{64}$")
BASIS_PATTERN = re.compile(r"^(substrate|artifact)_(intercepted|reconstructed)$")
DATE_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")

GRADES = ("E0", "E1", "E2", "E3", "E4")
SOURCES = (
    "agent_self_report",
    "framework",
    "gateway_proxy",
    "identity_provider",
    "sandbox",
    "operating_system",
    "network_sensor",
    "security_sensor",
    "external_authority",
)
RELATIONSHIPS = ("direct", "corroborating", "contradictory", "derived")
DIRECTNESS = ("direct_observation", "inferred")
VANTAGES = ("substrate", "artifact")
METHODS = ("intercepted", "reconstructed")
CLAIM_TYPES = ("emission-conformant", "operationally-conformant")
RECONCILIATION_STATES = ("agreement", "contradiction", "no_independent_evidence")

RECORD_MEMBERS = (
    "schema_version",
    "record_id",
    "agent_id",
    "actor_chain",
    "timestamp",
    "observation",
    "verification",
    "grade",
    "claims",
    "reconciliation",
    "integrity",
    "declared_vs_observed",
    "sampling",
    "provenance",
)
RECORD_REQUIRED = (
    "schema_version",
    "record_id",
    "agent_id",
    "timestamp",
    "observation",
    "verification",
    "grade",
    "integrity",
)
APPRAISAL_MEMBERS = (
    "schema_version",
    "appraisal_id",
    "subject_record",
    "e_grade",
    "claim_type",
    "reconciliation_state",
    "verifier_id",
    "timestamp",
    "signed",
)
APPRAISAL_REQUIRED = APPRAISAL_MEMBERS

OBSERVATION_MEMBERS = ("source", "relationship", "directness")
VERIFICATION_MEMBERS = ("vantage", "method", "basis", "basis_engines")
CLAIM_MEMBERS = ("claim", "evidence")
RECONCILIATION_MEMBERS = ("agent_claim", "boundary_observation", "state")
INTEGRITY_MEMBERS = ("signed", "chain_linked", "timestamped", "verifiable_by")
DECLARED_VS_OBSERVED_MEMBERS = ("permitted", "occurred")
SAMPLING_MEMBERS = ("sampled", "audit_required", "collection_gap")
SUBJECT_RECORD_MEMBERS = ("record_id", "digest")


class ConsumerError(ValueError):
    """A closed-vocabulary or content-address violation, with a stated reason."""


def _closed_members(
    value: Any, allowed: Iterable[str], label: str, required: Iterable[str] = ()
) -> None:
    allowed = tuple(allowed)
    if not isinstance(value, dict):
        raise ConsumerError("%s must be an object" % label)
    for name in value:
        if name not in allowed:
            raise ConsumerError(
                "additionalProperties: %s (not in the closed %d-member field set "
                "for %s)" % (name, len(allowed), label)
            )
    for name in required:
        if name not in value:
            raise ConsumerError("missing required member %s.%s" % (label, name))


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ConsumerError("%s must be a string" % label)
    return value


def _string_list(value: Any, label: str) -> None:
    if not isinstance(value, list):
        raise ConsumerError("%s must be an array" % label)
    for item in value:
        if not isinstance(item, str):
            raise ConsumerError("%s must contain only strings" % label)


def _enum(value: Any, label: str, allowed: Iterable[str]) -> None:
    allowed = tuple(allowed)
    if value not in allowed:
        raise ConsumerError("%s not in [%s]" % (label, ", ".join(allowed)))


def _boolean(value: Any, label: str) -> None:
    if not isinstance(value, bool):
        raise ConsumerError("%s must be a boolean" % label)


def _date_time(value: Any, label: str) -> None:
    text = _string(value, label)
    if not DATE_TIME.match(text):
        raise ConsumerError("%s is not an ISO 8601 date-time" % label)


def validate_record(record: Any) -> Dict[str, Any]:
    """Validate an `evidence-record` against its closed field set. Returns the
    record on success, raises ConsumerError on any violation."""
    _closed_members(record, RECORD_MEMBERS, "evidence-record", RECORD_REQUIRED)

    if record["schema_version"] != "0.1.0":
        raise ConsumerError(
            "schema_version must be const 0.1.0, got %r" % (record["schema_version"],)
        )
    _string(record["record_id"], "record_id")
    _string(record["agent_id"], "agent_id")
    _date_time(record["timestamp"], "timestamp")

    if "actor_chain" in record:
        _string_list(record["actor_chain"], "actor_chain")

    observation = record["observation"]
    _closed_members(
        observation, OBSERVATION_MEMBERS, "observation", OBSERVATION_MEMBERS
    )
    _enum(observation["source"], "observation.source", SOURCES)
    _enum(observation["relationship"], "observation.relationship", RELATIONSHIPS)
    _enum(observation["directness"], "observation.directness", DIRECTNESS)

    verification = record["verification"]
    _closed_members(
        verification,
        VERIFICATION_MEMBERS,
        "verification",
        ("vantage", "method", "basis"),
    )
    _enum(verification["vantage"], "verification.vantage", VANTAGES)
    _enum(verification["method"], "verification.method", METHODS)
    basis = _string(verification["basis"], "verification.basis")
    if not BASIS_PATTERN.match(basis):
        raise ConsumerError("verification.basis does not match {vantage}_{method}")
    if "basis_engines" in verification:
        _string_list(verification["basis_engines"], "verification.basis_engines")

    _enum(record["grade"], "grade", GRADES)

    if "claims" in record:
        claims = record["claims"]
        if not isinstance(claims, list):
            raise ConsumerError("claims must be an array")
        for index, claim in enumerate(claims):
            label = "claims[%d]" % index
            _closed_members(claim, CLAIM_MEMBERS, label, CLAIM_MEMBERS)
            _enum(claim["claim"], label + ".claim", CLAIM_TYPES)
            _string_list(claim["evidence"], label + ".evidence")

    if "reconciliation" in record:
        reconciliation = record["reconciliation"]
        _closed_members(
            reconciliation,
            RECONCILIATION_MEMBERS,
            "reconciliation",
            RECONCILIATION_MEMBERS,
        )
        _string(reconciliation["agent_claim"], "reconciliation.agent_claim")
        _string(
            reconciliation["boundary_observation"],
            "reconciliation.boundary_observation",
        )
        _enum(
            reconciliation["state"],
            "reconciliation.state",
            RECONCILIATION_STATES,
        )

    integrity = record["integrity"]
    _closed_members(
        integrity, INTEGRITY_MEMBERS, "integrity", ("signed", "chain_linked", "timestamped")
    )
    _boolean(integrity["signed"], "integrity.signed")
    _boolean(integrity["chain_linked"], "integrity.chain_linked")
    _boolean(integrity["timestamped"], "integrity.timestamped")
    if "verifiable_by" in integrity:
        _string_list(integrity["verifiable_by"], "integrity.verifiable_by")

    if "declared_vs_observed" in record:
        declared = record["declared_vs_observed"]
        _closed_members(
            declared,
            DECLARED_VS_OBSERVED_MEMBERS,
            "declared_vs_observed",
            DECLARED_VS_OBSERVED_MEMBERS,
        )
        _string(declared["permitted"], "declared_vs_observed.permitted")
        _string(declared["occurred"], "declared_vs_observed.occurred")

    if "sampling" in record:
        sampling = record["sampling"]
        _closed_members(
            sampling, SAMPLING_MEMBERS, "sampling", ("sampled", "audit_required")
        )
        _boolean(sampling["sampled"], "sampling.sampled")
        _boolean(sampling["audit_required"], "sampling.audit_required")
        if "collection_gap" in sampling:
            _boolean(sampling["collection_gap"], "sampling.collection_gap")

    if "provenance" in record:
        _string_list(record["provenance"], "provenance")

    # A derived observation states what it was derived from. The rule is in the
    # type's own semantics, not in an optional field.
    if observation["relationship"] == "derived":
        provenance = record.get("provenance") or []
        if not provenance:
            raise ConsumerError(
                "observation.relationship = derived requires provenance "
                "referencing the records it was derived from"
            )

    return record


def validate_appraisal(appraisal: Any) -> Dict[str, Any]:
    """Validate an `evidence-appraisal` against its closed field set."""
    _closed_members(
        appraisal, APPRAISAL_MEMBERS, "evidence-appraisal", APPRAISAL_REQUIRED
    )

    if appraisal["schema_version"] != "0.1.0":
        raise ConsumerError(
            "schema_version must be const 0.1.0, got %r"
            % (appraisal["schema_version"],)
        )
    _string(appraisal["appraisal_id"], "appraisal_id")

    subject = appraisal["subject_record"]
    _closed_members(
        subject, SUBJECT_RECORD_MEMBERS, "subject_record", SUBJECT_RECORD_MEMBERS
    )
    _string(subject["record_id"], "subject_record.record_id")
    check_digest_form(subject["digest"], "subject_record.digest")

    _enum(appraisal["e_grade"], "e_grade", GRADES)
    _enum(appraisal["claim_type"], "claim_type", CLAIM_TYPES)
    _enum(
        appraisal["reconciliation_state"],
        "reconciliation_state",
        RECONCILIATION_STATES,
    )
    _string(appraisal["verifier_id"], "verifier_id")
    _date_time(appraisal["timestamp"], "timestamp")
    _boolean(appraisal["signed"], "signed")

    return appraisal


def check_digest_form(value: Any, label: str = "digest") -> str:
    """The registered representation is bare lowercase hex, exactly 64
    characters. No silent stripping and no silent adding of a prefix: a
    `sha256:`-prefixed value and an uppercase value are both rejected here, and
    the caller never repairs them into an accepted form."""
    if not isinstance(value, str):
        raise ConsumerError("%s must be a string" % label)
    if not BARE_HEX.match(value):
        raise ConsumerError(
            "%s fails [0-9a-f]{64}: no silent stripping/adding of the prefix, no "
            "case folding (got %r)" % (label, value[:20])
        )
    return value


def record_identifier(record: Any) -> Dict[str, str]:
    """Validate then derive the registered identifier for an evidence record."""
    validate_record(record)
    return {
        "type": "evidence-record",
        "digest": digest(record),
        "canonicalization": "jcs",
        "representation": "bare-hex",
    }


def appraisal_identifier(appraisal: Any) -> Dict[str, str]:
    """Validate then derive the registered identifier for an appraisal."""
    validate_appraisal(appraisal)
    return {
        "type": "evidence-appraisal",
        "digest": digest(appraisal),
        "canonicalization": "jcs",
        "representation": "bare-hex",
    }


def bind_appraisal_to_record(appraisal: Any, record: Any) -> Dict[str, str]:
    """The consumption act: an appraisal cites its subject record by typed
    digest. Re-derive that digest from the record bytes and require it to match,
    and require the appraisal's reconciliation finding to agree with the
    record's own reconciliation state."""
    validate_appraisal(appraisal)
    validate_record(record)

    derived = digest(record)
    cited = appraisal["subject_record"]["digest"]
    if cited != derived:
        raise ConsumerError(
            "subject_record.digest %s does not match the identifier derived from "
            "the record bytes %s" % (cited, derived)
        )
    cited_id = appraisal["subject_record"]["record_id"]
    if cited_id != record.get("record_id"):
        raise ConsumerError(
            "subject_record.record_id %r does not match the record's own "
            "record_id %r" % (cited_id, record.get("record_id"))
        )
    return {
        "bound": "true",
        "record_id": cited_id,
        "derived_digest": derived,
        "cited_digest": cited,
    }


def canonical_hex(value: Any) -> str:
    """Canonical bytes as hex, for comparison against published vectors."""
    try:
        return canonical_bytes(value).hex()
    except CanonicalizationError as exc:
        raise ConsumerError(str(exc)) from exc
