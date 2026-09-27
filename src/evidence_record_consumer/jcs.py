"""RFC 8785 (JCS) canonicalization, restricted to the number-free field sets used
by the evidence-record and evidence-appraisal artifact types.

This is an independent implementation written against RFC 8785 and against the
published conflict-free vectors. It is deliberately narrow: it canonicalizes
exactly the JSON value space those field sets use (objects, arrays, strings,
booleans), and it refuses anything outside that space rather than guessing.

Rules implemented:

* Object member names are sorted by their UTF-16 code units (RFC 8785 section
  3.2.3). Sorting the UTF-16 big-endian encodings of the names gives exactly
  that order.
* No insignificant whitespace. Separators are "," and ":".
* Strings are escaped as ECMAScript JSON.stringify does, which is what RFC 8785
  section 3.2.2.2 requires: ", \\ and the control characters below 0x20 are
  escaped, the five short forms \\b \\t \\n \\f \\r are used where they apply,
  other control characters are written as \\u00xx, and every other character is
  emitted as UTF-8 without escaping.
* Lone surrogates are rejected. A string that cannot be encoded as UTF-8 is not
  a canonicalizable string.
* Numbers are refused. Both registered field sets are closed and number-free, so
  a number reaching this code is a defect in the record rather than something to
  serialize.
"""

from __future__ import annotations

import hashlib

__all__ = ["CanonicalizationError", "canonicalize", "canonical_bytes", "digest"]


class CanonicalizationError(ValueError):
    """Raised when a value cannot be canonicalized under the rules above."""


def _escape_string(value: str) -> str:
    out = ['"']
    for ch in value:
        code = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\f":
            out.append("\\f")
        elif ch == "\r":
            out.append("\\r")
        elif code < 0x20:
            out.append("\\u%04x" % code)
        elif 0xD800 <= code <= 0xDFFF:
            raise CanonicalizationError(
                "lone surrogate U+%04X cannot be encoded as UTF-8" % code
            )
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _key_order(name: str) -> bytes:
    return name.encode("utf-16-be")


def canonicalize(value) -> str:
    """Return the JCS canonical form of *value* as a str."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        raise CanonicalizationError("null is outside the closed field sets")
    if isinstance(value, (int, float)):
        raise CanonicalizationError(
            "numbers are outside the closed number-free field sets"
        )
    if isinstance(value, str):
        return _escape_string(value)
    if isinstance(value, list):
        return "[" + ",".join(canonicalize(item) for item in value) + "]"
    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise CanonicalizationError("object member names must be strings")
        members = sorted(value.items(), key=lambda kv: _key_order(kv[0]))
        body = ",".join(
            _escape_string(key) + ":" + canonicalize(item) for key, item in members
        )
        return "{" + body + "}"
    raise CanonicalizationError(
        "unsupported type for canonicalization: %s" % type(value).__name__
    )


def canonical_bytes(value) -> bytes:
    """Return the JCS canonical form of *value* as UTF-8 octets."""
    return canonicalize(value).encode("utf-8")


def digest(value) -> str:
    """Return the derived identifier: bare lowercase SHA-256 hex of the
    canonical form, which is the representation the registry entry registers."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()
