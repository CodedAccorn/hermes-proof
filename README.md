# HermesProof v0.2

HermesProof independently evaluates explicit, deterministic local-file requirements and writes auditable JSON evidence. It preserves the MVP `proof_verify` and `proof_report` tool names and calling conventions.

This is the hackathon release. It verifies declared conditions; it does **not** infer whether an entire task is complete, treat tool success as outcome proof, or enforce policy through passive hooks.

## What v0.2 implements

- Strict contracts for `file_exists`, `file_contains`, `file_sha256`, and local-file `json_equals`.
- Exactly three outcomes: `verified`, `failed`, and `unverified`.
- Evidence IDs, UTC timestamps, expected/observed values, check-level status, and verification root.
- Atomic JSON persistence and retrieval by report ID or latest report.
- Root confinement, absolute/traversal rejection, symlink/junction escape checks, a 1 MiB content limit, and fail-closed parsing.
- No LLM judging, shell execution, credential handling, or network requests in v0.2 verification handlers.

## Architecture

| Module | Responsibility |
|---|---|
| `contracts.py` | Strict request parsing and supported check definitions |
| `engine.py` | Deterministic, root-confined file evaluation |
| `evidence.py` | Atomic persistent report storage and retrieval |
| `handlers.py` | Backward-compatible tool handlers and aggregate status |
| `schemas.py` | Hermes-facing JSON schemas |
| `tools.py` | Stable public import surface for the MVP tool names |

File verification defaults to the gateway working directory. Set `HERMES_PROOF_ROOT` to the project directory the gateway is allowed to verify. Evidence defaults to `.hermes-proof/evidence` under the gateway working directory; set `HERMES_PROOF_DATA_DIR` to a stable gateway-owned directory for production-like runs. Evidence survives process/gateway restarts when the working directory or configured data directory remains the same.

## Contracts

```json
{
  "label": "release artifact",
  "checks": [
    {"name": "marker", "type": "file_contains", "target": "demo.txt", "expected": "DEPLOYED"},
    {"name": "state", "type": "json_equals", "target": "state.json", "path": "$.release.ready", "expected": true}
  ]
}
```

`json_equals.path` supports `$` and dot-separated object keys/list indexes such as `$.release.items.0`. Malformed contracts and inaccessible or unsafe targets are `unverified`; an observed mismatch is `failed`.

## Install and Hermes validation

Copy the directory to `~/.hermes/plugins/hermes-proof` (or `%LOCALAPPDATA%\hermes\plugins\hermes-proof` on native Windows), enable it using the instructions for your installed Hermes version, then run that version's plugin doctor/validation command. The manifest advertises tools only; no lifecycle hook signature has been assumed.

### Native validation record

On 2026-11-11, the v0.2 tools were manually validated through a native Hermes Windows session with `HERMES_PROOF_ROOT` set to the project directory:

- A matching `file_contains` check returned `verified` with persisted report `d41c8682-0995-4c08-bac5-6fac3736a1a0`.
- The same contract against changed content returned `failed` with persisted report `52b18913-5e27-4c29-b3f8-9166597db34d`.
- Both reports were retrieved successfully by ID after a Hermes gateway restart.
- `hermes plugins doctor ... --ci` completed successfully against the installed plugin.

This records plugin-doctor success, live tool execution, and restart persistence. Lifecycle-hook compatibility remains outside the v0.2 scope and is not claimed.

## Demo

Run the standalone demonstration:

```bash
python demo.py
```

It produces a `verified` positive result, changes the observed artifact, produces `failed`, then retrieves the persisted negative report by ID. In Hermes, the equivalent call is:

```json
{"label":"demo deployment","checks":[{"type":"file_contains","target":"demo.txt","expected":"DEPLOYED"}]}
```

## Test

```bash
python -m pytest -q
```

The suite covers positive/negative MVP regression behavior, malformed contracts, inaccessible content targets, traversal, absolute paths, symlink escape where the OS permits creating one, hashes, JSON paths, persistence, and report-ID traversal.

## v1.0 roadmap (not implemented)

- Hardened HTTPS verification with pinned destinations, public-address policy, redirect revalidation, DNS-rebinding resistance, response limits, and credential redaction.
- Lifecycle association and policy-driven enforcement only where verified against the installed official Hermes plugin API.
- Retention/indexing, signatures or tamper evidence, richer audit queries, and concurrency hardening for multiple gateway processes.

These are future capabilities, not v0.2 claims.
