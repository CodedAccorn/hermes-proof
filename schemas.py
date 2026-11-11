"""JSON schemas exposed to Hermes for the v0.2 tool interface."""

CHECK_TYPES = ["file_exists", "file_contains", "file_sha256", "json_equals"]

CHECK = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "name": {"type": "string", "minLength": 1, "maxLength": 120},
        "type": {"type": "string", "enum": CHECK_TYPES},
        "target": {"type": "string", "minLength": 1, "maxLength": 4096},
        "expected": {},
        "path": {"type": "string", "maxLength": 1024},
    },
    "required": ["type", "target"],
}

VERIFY = {
    "name": "proof_verify",
    "description": (
        "Deterministically verify explicit local-file outcome conditions and persist an "
        "evidence report. This verifies only the declared contract; it does not enforce task completion."
    ),
    "parameters": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "checks": {"type": "array", "minItems": 1, "maxItems": 20, "items": CHECK},
            "label": {"type": "string", "maxLength": 200},
        },
        "required": ["checks"],
    },
}

REPORT = {
    "name": "proof_report",
    "description": "Retrieve a persisted HermesProof evidence report by ID, or the latest report.",
    "parameters": {
        "type": "object",
        "additionalProperties": False,
        "properties": {"report_id": {"type": "string", "format": "uuid"}},
    },
}
