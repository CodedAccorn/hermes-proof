"""Atomic, durable evidence report storage."""
import json
import os
import re
import threading
from pathlib import Path
from typing import Any

_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I)
_LOCK = threading.RLock()


def data_dir() -> Path:
    try:
        from hermes_constants import get_hermes_home
        home = Path(get_hermes_home())
    except ImportError:
        configured = os.environ.get("HERMES_HOME")
        if not configured:
            raise RuntimeError("Hermes profile home is unavailable") from None
        home = Path(configured)
    return home.expanduser().resolve(strict=False) / "hermes-proof" / "evidence"


def save(report: dict[str, Any]) -> None:
    directory = data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{report['id']}.json"
    temporary = directory / f".{report['id']}.tmp"
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    with _LOCK:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        latest_tmp = directory / ".latest.tmp"
        latest_tmp.write_text(report["id"], encoding="ascii")
        os.replace(latest_tmp, directory / "latest")


def load(report_id: str | None = None) -> dict[str, Any] | None:
    directory = data_dir()
    with _LOCK:
        if report_id is None:
            try:
                report_id = (directory / "latest").read_text(encoding="ascii").strip()
            except OSError:
                return None
        if not isinstance(report_id, str) or not _ID.fullmatch(report_id):
            raise ValueError("report_id must be a valid UUID")
        try:
            value = json.loads((directory / f"{report_id}.json").read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError):
            raise ValueError("stored report is inaccessible or corrupt") from None
        return value
