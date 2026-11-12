# HermesProof v0.2 audit

## Baseline findings

The audited v0.1 MVP exposed `proof_verify` and `proof_report`, supported positive and negative file checks, and rejected traversal through `Path.resolve`. Its tests covered one positive, one negative, one traversal case, and disabled HTTP.

Release-critical defects found:

1. Evidence existed only in a process-global list and was lost on restart.
2. Check statuses used `passed` while aggregate status used `verified`, weakening the status contract.
3. Request validation allowed unknown fields and deferred malformed items into broad exception handling.
4. `json_equals` was categorized as an HTTP operation and was never usable for local JSON.
5. Hash verification and report retrieval by ID were absent.
6. Missing content targets were reported as ordinary failures rather than inaccessible/unverified observations.
7. The manifest advertised `post_tool_call`, but no installed Hermes executable/API was available to validate the hook signature.
8. Documentation described in-memory evidence and an early preview rather than a restart-durable hackathon release.

## v0.2 decisions

- Keep both MVP tool names and the direct-list/wrapped-payload invocation forms.
- Use strict, dependency-free Python contract parsing in addition to Hermes-facing JSON schemas.
- Treat malformed, unsupported, unsafe, inaccessible, oversized, non-UTF-8, and invalid-JSON checks as `unverified`.
- Treat deterministic observed mismatches as `failed` and matches as `verified`.
- Persist one immutable JSON file per report and atomically update a latest-report pointer.
- Remove lifecycle hooks from the v0.2 manifest/registration until an installed official Hermes API can validate them.
- Keep all network verification out of v0.2; HTTP security belongs to the v1.0 hardened transport.
- Require an explicitly configured verification root; never infer it from the process working directory.
- Refuse active Hermes-profile and credential-like targets before reading them.
- Store evidence beneath the active profile returned by Hermes' official `get_hermes_home()` API.

## Validation record and boundary

The local automated suite and standalone demo validate the Python implementation. On 2026-11-11, the installed plugin passed `hermes plugins doctor ... --ci`. A native Hermes Windows session additionally produced the expected `verified` and `failed` results, retrieved both reports by ID, restarted the gateway, and retrieved both reports again successfully. This validates the manifest/registration path, live tool execution, and restart persistence for that installation.

Lifecycle integration remains outside v0.2 and is not claimed by this record.
