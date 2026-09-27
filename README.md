# evidence-record-consumer

A consumer of the two registered artifact types `evidence-record` and
`evidence-appraisal`: it resolves each type by name, applies the closed field
sets and closed vocabularies the registration declares, re-derives each
artifact's identifier from the registered derived-identifier context, and binds
an appraisal to the record it cites by typed digest.

The types are registered in the Canonical Payload Binding Artifact Type Registry
(`action-state-group/scitt-payload-binding`, entry PR #76), owned by Empire Labs
Pty Ltd.

**Status:** prototype  ·  **Licence:** Apache-2.0  ·  **Language:** Python 3.10+, standard library only

## What this is, and what it is not

It **is** a consumer of the registered types. It applies the closed 14-member
field set of an evidence record and the closed 9-member field set of an
appraisal, refuses an unrecognised value everywhere rather than tolerating it,
and re-derives the content address from the registered context: SHA-256 over the
JCS (RFC 8785) canonical form of the full artifact, no member removal, no domain
separation, bare lowercase hex.

It **is not** a specification, it is not the producer of either type, and it
does not implement appraisal. It does not decide grades, it does not model the
mechanism behind any rung of the E0-E4 ladder, and it verifies no signature,
timestamp or inclusion proof. It reads published artifacts and checks that they
obey the type they claim to be.

Why it exists: Gate B of the registry's Designated Expert admission checklist
asks an entry to name a consuming profile, a distinct specification or
deployment that uses the registered name in a normatively stated way, and states
that the entry's own specification does not count. The two entries were naming
each other inside one specification family. This repository is the consumer
named instead.

## Reproduce it in one command

```bash
PYTHONPATH=src python3 -m evidence_record_consumer vectors \
  vectors/evidence-record-vectors-v0.1.json \
  vectors/evidence-appraisal-vectors-v0.1.json \
  --samples samples
```

The published vector sets are vendored at a pinned commit (see
[PROVENANCE.md](PROVENANCE.md)). Expected output, from the run recorded when this
repository was published:

```
PASS  er-kat-01-e0-self-report                       canonical bytes match (810 bytes); digest matches f0d60fe6926c2837
PASS  er-kat-02-e2-emission-conformant               canonical bytes match (887 bytes); digest matches 283e363d9ce385c2
PASS  er-kat-03-e4-operationally-conformant          canonical bytes match (1047 bytes); digest matches c65a52c39246a73f
PASS  er-kat-04-e3-contradiction                     canonical bytes match (873 bytes); digest matches 2a9af62bddd1513f
PASS  er-kat-05-e3-derived-reconstructed             canonical bytes match (939 bytes); digest matches c914624093331a20
PASS  er-fail-01-unregistered-grade                  rejected: grade not in [E0, E1, E2, E3, E4]
PASS  er-fail-02-unregistered-reconciliation-state   rejected: reconciliation.state not in [agreement, contradiction, no_independent_evidence]
PASS  er-fail-03-unregistered-observation-relationship rejected: observation.relationship not in [direct, corroborating, contradictory, derived]
PASS  er-fail-04-float-member                        rejected: additionalProperties: confidence (not in the closed 3-member field set for observation)
PASS  er-fail-05-representation-confusion            bare form accepted, prefixed form rejected: digest fails [0-9a-f]{64}: no silent stripping/adding of the prefix, no case folding
PASS  er-fail-06-uppercase-hex                       digest fails [0-9a-f]{64}: no silent stripping/adding of the prefix, no case folding
PASS  er-fail-07-mutation-probe-single-byte          mutated digest 3db8eaa14c87bb1d differs from the pinned c65a52c39246a73f
PASS  ea-kat-01-e4-agreement                         canonical bytes match (345 bytes); digest matches 916265d4e0b36453
PASS  ea-kat-02-e0-no-independent-evidence           canonical bytes match (354 bytes); digest matches 4f7809f8726d8737
PASS  ea-kat-03-e3-contradiction                     canonical bytes match (348 bytes); digest matches 7fe859560c3b0ee9
PASS  ea-fail-01-grade-in-producer-record            additionalProperties: e_grade (not in the closed 14-member field set for evidence-record)
PASS  ea-fail-02-unregistered-grade                  rejected: e_grade not in [E0, E1, E2, E3, E4]
PASS  ea-fail-03-unregistered-claim-type             rejected: claim_type not in [emission-conformant, operationally-conformant]
PASS  ea-fail-04-subject-digest-not-bare-hex         rejected: subject_record.digest fails [0-9a-f]{64}: no silent stripping/adding of the prefix, no case folding
PASS  ea-fail-05-mutation-probe-single-byte          mutated digest 2b004b3032e34048 differs from the pinned 916265d4e0b36453
vectors: 8 positives reproduced, 12 MUST-FAIL cases exercised, 0 FAILED
```

Eight positives reproduce the publisher's canonical bytes and digests exactly.
Twelve MUST-FAIL cases are rejected, each for the reason the vector states rather
than for a reason of this implementation's own, so a green run is not a
coincidence.

## The consumption act

An appraisal cites the record it appraises by typed digest. That binding is the
reason the type exists, so it is checkable from the bytes:

```bash
PYTHONPATH=src python3 -m evidence_record_consumer record \
  samples/er-00003-e4-operationally-conformant.json

PYTHONPATH=src python3 -m evidence_record_consumer appraisal \
  samples/ea-00001-e4-agreement.json \
  --record samples/er-00003-e4-operationally-conformant.json
```

```
ACCEPT evidence-record
  derived identifier (jcs, bare-hex): c65a52c39246a73f58f4d185b104ba1c1237e25198c5b5deeab1de77e80232a1
ACCEPT evidence-appraisal
  derived identifier (jcs, bare-hex): 916265d4e0b36453ff809042385b571dd785cc56025366fbe53823a951dc030a
  bound to er-00003 at c65a52c39246a73f58f4d185b104ba1c1237e25198c5b5deeab1de77e80232a1 (subject digest re-derived from the record bytes)
```

An appraisal paired with the wrong record is rejected, which is what makes the
binding worth having:

```
REJECT binding: subject_record.digest 2a9af62bddd1513f8cdaa3c7046e8b921e87f700caff67ca14cd0d174c2b7aa7
does not match the identifier derived from the record bytes c65a52c39246a73f58f4d185b104ba1c1237e25198c5b5deeab1de77e80232a1
```

## What is implemented

| Rule | Implementation |
|---|---|
| Canonicalization | RFC 8785 JCS over the closed, number-free field sets. Member names sorted by UTF-16 code units, no whitespace, ECMAScript string escaping, lone surrogates refused, numbers refused rather than serialized |
| Closed field sets | 14 members for a record, 9 for an appraisal, nested sets likewise closed. An unknown member is a rejection with the member named, never a silent drop |
| Closed vocabularies | Grades E0 to E4, reconciliation `agreement / contradiction / no_independent_evidence`, claim types, observation source, relationship and directness, vantage and method with the derived basis |
| Representation | Bare lowercase 64-character hex. A `sha256:`-prefixed value and an uppercase value are both rejected, and neither is repaired into an accepted form |
| Derived identifier | SHA-256 over the canonical form of the full artifact, no domain separation, no member removal |
| Typed-digest binding | An appraisal binds to the record it cites, with the digest re-derived from the record bytes, and the record identifier must agree between the two artifacts |

Two rules worth stating plainly, because they are the ones a consumer can get
wrong:

1. **Closed vocabularies fail closed.** An unrecognised value is a failure, never
   an informational pass and never a new rung, so a typo cannot silently raise or
   lower an artifact's strength. This deliberately inverts the never-reject
   invariant of the payload binding specification at the layer where these types
   live.
2. **The grade is an appraisal output.** An evidence record that stamps its own
   strength is rejected: `e_grade` is not a member of the record's closed field
   set. That is the RATS split carried into the types, evidence in, appraisal as
   the bridge, attestation results out.

## Tests

```bash
PYTHONPATH=src python3 -m pytest tests -q
```

## Boundaries

- A green run proves conformance to the published vectors. It is not an
  endorsement, an admission to any registry and not a statement by any Designated
  Expert.
- This is a consumer, not a verifier. It makes no cryptographic claim beyond
  re-deriving a content address, and it deliberately does not touch the
  mechanism behind any evidence grade.
- The field sets and vocabularies implemented here are read from the registered
  types. Where this implementation and the registration disagree, the
  registration governs and this is a bug.

## Provenance and attribution

Built by [Empire Labs Pty Ltd](https://empirelabs.com.au). The vendored vectors
and samples are the owner's published set for these types, vendored at a pinned
commit with per-file hashes recorded in [PROVENANCE.md](PROVENANCE.md). Licensed
under Apache-2.0, see [LICENSE](LICENSE) and [NOTICE](NOTICE). Commits carry a
DCO sign-off.

No third-party dependencies: the runtime and the vector run use the Python
standard library, with `pytest` as a test-only requirement. There is no
third-party code here to acknowledge, and the vendored vectors and samples are
the publisher's own published set rather than another project's work.
