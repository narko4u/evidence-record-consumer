# Provenance of the vendored vectors and samples

The `samples/` and `vectors/` directories are not authored here. They are the
publisher's own published conformance set for the two registered artifact types,
vendored so that a reader can run the whole suite without cloning a second
repository.

| Field | Value |
|---|---|
| Source repository | `narko4u/evidence-record-spec` |
| Source revision | `a23fbd6678542d4a4c93be266ebff86df7326217` (public `main`) |
| Source licence | Apache-2.0 |
| Vendored paths | `samples/`, `vectors/cpb-registry/` |
| Verification | `PROVENANCE.sha256` (SHA-256 per file) |

Check the vendored bytes against the recorded hashes from the repository root:

```bash
sha256sum -c PROVENANCE.sha256
```

The recorded hashes were compared against the same files fetched from the source
repository at the pinned revision above, so the bytes here and the bytes there
are the same bytes, not merely files of the same name:

| File | SHA-256 |
|---|---|
| `samples/ea-00001-e4-agreement.json` | `17d3a8b9ad4a8d8f7495cac43e736666284b3f3265235e887ecc77744bddcdd5` |
| `samples/ea-00002-e0-no-independent-evidence.json` | `b2966f737a645a7167014825493d236db1ad45d5c247e6b9ec7ad73cad9efffe` |
| `samples/ea-00003-e3-contradiction.json` | `42bb9cc15cd93e92b63cbdf20b8fe2841983d438e2c997db7d3b048eb2167265` |
| `samples/er-00001-e0-self-report.json` | `02049e8fec98fbfd90dc212468166d9a7695ada5bff078d547e4fd5e5dc7ddd5` |
| `samples/er-00002-e2-emission-conformant.json` | `268ea433346b5c6fb09e4c74eb57bd11e72303141f26161d822a2816256995d4` |
| `samples/er-00003-e4-operationally-conformant.json` | `cf6e7e0bc69be95408cd0e2a237774c3f62813509508e3cc6bd935e6d78a4da0` |
| `samples/er-00004-e3-contradiction.json` | `92982a30398644812a35c914f34e7aab904c206997f7333b2d28310caf117c63` |
| `samples/er-00005-e3-derived-reconstructed.json` | `b2b4c8285f3cb8fb254d1c6b77b29b78ed086841955525ac4e01fea10cb1be6c` |
| `vectors/evidence-appraisal-vectors-v0.1.json` | `d565be154b3b241b33e00cf0f04a6758ae07cec604966017c322683701238e88` |
| `vectors/evidence-record-vectors-v0.1.json` | `b8e54a9b38d7caca9d4dc4cd74f8b2f6097ec5622badefa7ff58dd45b0096c87` |

The code in `src/` and `tests/` is original to this repository and shares no code
with the source repository. It is an independent implementation written against
the published schemas and vector descriptions, which is the point: a consumer
that reused the publisher's own canonicalizer would demonstrate nothing about the
registration.

## Dependencies

None. The runtime and the test run use the Python standard library, plus `pytest`
as a test-only requirement. There is deliberately no dependency on the source
repository's tooling, so a green run here cannot be inherited from there.
