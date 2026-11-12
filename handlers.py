"""Backward-compatible HermesProof native tool handlers."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

try:
    from . import contracts, engine, evidence
except ImportError:  # Standalone plugin-loader/test compatibility.
    import contracts
    import engine
    import evidence


def _json(value):
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def proof_verify(checks=None, label="", **kwargs):
    configured_root = kwargs.pop("_verification_root", None)
    if isinstance(checks, dict):
        payload = checks
        unknown = set(payload) - {"checks", "label"}
        if unknown:
            return _json({"status": "unverified", "error": f"unsupported request fields: {', '.join(sorted(unknown))}"})
        checks = payload.get("checks")
        label = payload.get("label", label)
    elif checks is None:
        checks = kwargs.get("checks")
        label = kwargs.get("label", label)
    try:
        parsed, label = contracts.parse_request(checks, label)
    except contracts.ContractError as exc:
        return _json({"status": "unverified", "error": str(exc)})

    configured_root = configured_root or os.environ.get("HERMES_PROOF_ROOT")
    if not isinstance(configured_root, (str, os.PathLike)) or not str(configured_root).strip():
        return _json({"status": "unverified", "error": "verification root is not configured"})
    root = Path(configured_root).expanduser()
    try:
        root = root.resolve(strict=True)
        if not root.is_dir():
            raise OSError
    except (OSError, RuntimeError):
        return _json({"status": "unverified", "error": "verification root is not an accessible directory"})
    results = []
    for item in parsed:
        try:
            status, details = engine.evaluate(item, root)
        except engine.UnverifiableError as exc:
            status, details = "unverified", {"reason": str(exc), "expected": item.expected}
        results.append({
            "name": item.name, "type": item.type, "target": item.target,
            "status": status, "evidence": details,
        })
    overall = (
        "failed" if any(item["status"] == "failed" for item in results)
        else "unverified" if any(item["status"] == "unverified" for item in results)
        else "verified"
    )
    report = {
        "schema_version": "0.2", "id": str(uuid4()), "label": label,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "verification_root": str(root.resolve()), "status": overall, "checks": results,
    }
    try:
        evidence.save(report)
    except (OSError, RuntimeError) as exc:
        report["status"] = "unverified"
        report["persistence_error"] = f"evidence could not be persisted: {exc.__class__.__name__}"
    return _json(report)


def proof_report(report_id=None, **kwargs):
    if isinstance(report_id, dict):
        payload = report_id
        unknown = set(payload) - {"report_id"}
        if unknown:
            return _json({"status": "unverified", "error": f"unsupported request fields: {', '.join(sorted(unknown))}"})
        report_id = payload.get("report_id")
    elif report_id is None:
        report_id = kwargs.get("report_id")
    try:
        report = evidence.load(report_id)
    except (ValueError, RuntimeError) as exc:
        return _json({"status": "unverified", "error": str(exc)})
    if report is None:
        return _json({"status": "unverified", "reason": "No matching persisted verification report exists"})
    return _json(report)
