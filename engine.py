"""Deterministic local-file verification. This module never executes a shell."""
import hashlib
import json
import os
from pathlib import Path
from typing import Any

try:
    from .contracts import CheckContract
except ImportError:  # Standalone plugin-loader/test compatibility.
    from contracts import CheckContract

MAX_CONTENT_BYTES = 1024 * 1024


class UnverifiableError(ValueError):
    """A check could not be safely or deterministically evaluated."""


def _safe_file(target: str, root: Path) -> Path:
    if "\x00" in target:
        raise UnverifiableError("target contains a null byte")
    candidate = Path(target)
    if candidate.is_absolute():
        raise UnverifiableError("absolute file targets are forbidden")
    root = root.resolve(strict=True)
    joined = root / candidate
    try:
        resolved = joined.resolve(strict=False)
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        raise UnverifiableError("file target escapes the verification root") from None
    ancestor = joined
    while not ancestor.exists() and ancestor != root:
        ancestor = ancestor.parent
    try:
        ancestor.resolve(strict=True).relative_to(root)
    except (OSError, RuntimeError, ValueError):
        raise UnverifiableError("file target escapes through a link") from None
    return resolved


def _read_bytes(path: Path) -> bytes:
    try:
        if not path.is_file():
            raise UnverifiableError("target is not an accessible regular file")
        if path.stat().st_size > MAX_CONTENT_BYTES:
            raise UnverifiableError("file exceeds the 1 MiB content-check limit")
        with path.open("rb") as handle:
            data = handle.read(MAX_CONTENT_BYTES + 1)
        if len(data) > MAX_CONTENT_BYTES:
            raise UnverifiableError("file changed or exceeds the 1 MiB content-check limit")
        return data
    except UnverifiableError:
        raise
    except OSError as exc:
        raise UnverifiableError(f"file is inaccessible: {exc.__class__.__name__}") from None


def _json_path(value: Any, path: str | None) -> Any:
    if path in (None, "", "$"):
        return value
    if not path.startswith("$."):
        raise UnverifiableError("JSON path must be '$' or a dot-separated path beginning with '$.'")
    current = value
    for part in path[2:].split("."):
        if not part:
            raise UnverifiableError("JSON path contains an empty segment")
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            raise UnverifiableError("JSON path was not found")
    return current


def evaluate(contract: CheckContract, root: Path | None = None) -> tuple[str, dict[str, Any]]:
    root = Path(os.environ.get("HERMES_PROOF_ROOT", Path.cwd())) if root is None else root
    path = _safe_file(contract.target, root)
    if contract.type == "file_exists":
        try:
            exists = path.is_file()
        except OSError as exc:
            raise UnverifiableError(f"file status is inaccessible: {exc.__class__.__name__}") from None
        return ("verified" if exists else "failed"), {"observed": exists, "expected": True}
    data = _read_bytes(path)
    if contract.type == "file_contains":
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise UnverifiableError("file is not valid UTF-8") from None
        observed = contract.expected in text
        return ("verified" if observed else "failed"), {
            "observed": {"contains_expected": observed}, "expected": contract.expected
        }
    if contract.type == "file_sha256":
        observed = hashlib.sha256(data).hexdigest()
        expected = contract.expected.lower()
        return ("verified" if observed == expected else "failed"), {
            "observed": observed, "expected": expected
        }
    if contract.type == "json_equals":
        try:
            document = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise UnverifiableError("target is not valid UTF-8 JSON") from None
        observed = _json_path(document, contract.path)
        return ("verified" if observed == contract.expected else "failed"), {
            "observed": observed, "expected": contract.expected, "path": contract.path or "$"
        }
    raise UnverifiableError("unsupported check type")
