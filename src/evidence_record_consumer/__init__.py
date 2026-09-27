"""A consumer of the registered `evidence-record` and `evidence-appraisal`
artifact types.

The artifact types are registered in the Canonical Payload Binding Artifact Type
Registry. This package consumes them: it applies the closed field sets and closed
vocabularies the registration declares, re-derives each artifact's identifier
from the registered derived-identifier context, and binds an appraisal to the
record it cites by typed digest.

It is a consumer and not a specification. It does not implement appraisal: it
does not decide grades, and it does not model the mechanism behind any rung of
the E0-E4 ladder. It reads what a producer and a verifier published and checks
that the published artifacts obey the type they claim to be.
"""

from .consumer import (
    APPRAISAL_MEMBERS,
    RECORD_MEMBERS,
    ConsumerError,
    appraisal_identifier,
    bind_appraisal_to_record,
    check_digest_form,
    record_identifier,
    validate_appraisal,
    validate_record,
)
from .consumer import canonical_bytes, digest
from .jcs import CanonicalizationError, canonicalize

__version__ = "0.1.0"

__all__ = [
    "APPRAISAL_MEMBERS",
    "RECORD_MEMBERS",
    "CanonicalizationError",
    "ConsumerError",
    "__version__",
    "appraisal_identifier",
    "bind_appraisal_to_record",
    "canonical_bytes",
    "canonicalize",
    "check_digest_form",
    "digest",
    "record_identifier",
    "validate_appraisal",
    "validate_record",
]
