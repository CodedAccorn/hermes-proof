"""Strict verification-contract parsing for HermesProof v0.2."""
from dataclasses import dataclass
from typing import Any

SUPPORTED_TYPES = frozenset({"file_exists", "file_contains", "file_sha256", "json_equals"})
_ALLOWED_KEYS = frozenset({"name", "type", "target", "expected", "path"})


class ContractError(ValueError):
    """The requested verification contract is malformed or unsupported."""


@dataclass(frozen=True)
class CheckContract:
    type: str
    target: str
    expected: Any = None
    path: str | None = None
    name: str | None = None


def parse_check(value: Any) -> CheckContract:
    if not isinstance(value, dict):
        raise ContractError("check must be an object")
    unknown = set(value) - _ALLOWED_KEYS
    if unknown:
        raise ContractError(f"unsupported check fields: {', '.join(sorted(unknown))}")
    kind = value.get("type")
    target = value.get("target")
    if kind not in SUPPORTED_TYPES:
        raise ContractError("unsupported check type")
    if not isinstance(target, str) or not target or len(target) > 4096:
        raise ContractError("target must be a non-empty string of at most 4096 characters")
    name = value.get("name")
    if name is not None and (not isinstance(name, str) or not name or len(name) > 120):
        raise ContractError("name must be a non-empty string of at most 120 characters")
    path = value.get("path")
    if path is not None and (not isinstance(path, str) or len(path) > 1024):
        raise ContractError("path must be a string of at most 1024 characters")
    if kind == "file_exists":
        if "expected" in value or path is not None:
            raise ContractError("file_exists does not accept expected or path")
    elif "expected" not in value:
        raise ContractError(f"{kind} requires expected")
    if kind in {"file_contains", "file_sha256"} and not isinstance(value.get("expected"), str):
        raise ContractError(f"{kind} expected must be a string")
    if kind == "file_sha256":
        digest = value["expected"]
        if len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
            raise ContractError("file_sha256 expected must be a 64-character hexadecimal digest")
    if kind != "json_equals" and path is not None:
        raise ContractError("path is supported only by json_equals")
    return CheckContract(kind, target, value.get("expected"), path, name)


def parse_request(checks: Any, label: Any = "") -> tuple[list[CheckContract], str]:
    if not isinstance(checks, list) or not 1 <= len(checks) <= 20:
        raise ContractError("checks must contain between 1 and 20 items")
    if not isinstance(label, str) or len(label) > 200:
        raise ContractError("label must be a string of at most 200 characters")
    return [parse_check(item) for item in checks], label
