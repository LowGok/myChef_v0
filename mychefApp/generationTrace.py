"""Optional local records of menu generation for reproducible product tests."""

import json
import os
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone


def start_trace(model, prompt, system_instruction, temperature):
    directory = os.environ.get("MYCHEF_TRACE_DIR")
    if not directory:
        return None
    path = Path(directory) / uuid4().hex
    path.mkdir(parents=True, mode=0o700)
    (path / "request.json").write_text(json.dumps({
        "model": model, "prompt": prompt, "system_instruction": system_instruction,
        "temperature": temperature,
    }, indent=2), encoding="utf-8")
    return path


def finish_trace(path, *, response=None, error=None):
    if path is None:
        return
    if error is not None:
        # Exception strings can contain URLs with API keys.
        result = {"error_type": type(error).__name__, "status_code": getattr(error, "code", None)}
        (path / "error.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    else:
        (path / "response.txt").write_text(response or "", encoding="utf-8")


def record_stage(stage, **data):
    directory = os.environ.get("MYCHEF_TRACE_DIR")
    if not directory:
        return
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    with (path / "events.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"time": datetime.now(timezone.utc).isoformat(),
                                 "stage": stage, **data}) + "\n")
