"""Checkpoint support — JSONL-based resume for long test-generation runs.

Each line of the checkpoint file is one JSON object describing a completed
test file. On a re-run, tests that are already recorded are skipped, so an
interrupted `generate` run does not have to re-call the LLM (the slow, costly
step) for work that already finished.

The checkpoint intentionally stores the full MethodInfo of each completed
test, so a resumed run can rebuild a report identical to a full run.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict

from method_extractor import MethodInfo


def load_checkpoint(path: Path) -> Dict[str, dict]:
    """Load the checkpoint file, keyed by test class name.

    Returns {} if the file does not exist. Malformed lines are skipped.
    """
    if not path.is_file():
        return {}
    done: Dict[str, dict] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("class_name"):
                done[record["class_name"]] = record
    return done


def append_checkpoint(path: Path, record: dict) -> None:
    """Append one record to the checkpoint file (creates dir/file if needed)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def make_record(
    method: MethodInfo, class_name: str, file_path: Path, target: str
) -> dict:
    """Build a checkpoint record for one completed test file."""
    return {
        "class_name": class_name,
        "file_path": str(file_path),
        "target": target,
        "method": asdict(method),
    }
