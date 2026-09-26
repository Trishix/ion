from __future__ import annotations

import re
import shlex
from pathlib import Path

from ion.contracts import Outcome, VerificationEvidence, VerificationRecord
from ion.workspace import ChangeSet


class CompletionGate:
    def decide(self, changed: ChangeSet, records: list[VerificationRecord], final_fingerprint: str) -> Outcome:
        if changed.ambiguous_files:
            return Outcome.unverified
        if not changed.attributable_files:
            return Outcome.unverified
        if not any(record.status == "passed" and record.workspace_fingerprint == final_fingerprint for record in records):
            return Outcome.unverified
        return Outcome.verified


def observe_pytest(command: str, output: str, exit_code: int, operation_id: str, fingerprint: str, changed_files: tuple[str, ...]) -> VerificationRecord | None:
    if "pytest" not in command or exit_code != 0:
        return None
    try:
        parts = shlex.split(command)
    except ValueError:
        return None
    if any(part in {"&&", "||", ";", "|", ">", "<"} for part in parts):
        return None
    pytest_entry = parts[0] == "pytest" or (len(parts) >= 3 and Path(parts[0]).name.startswith("python") and parts[1:3] == ["-m", "pytest"])
    if not pytest_entry:
        return None
    targets = [part for part in parts if part.endswith(".py") or part.startswith("tests/")]
    if not targets:
        return None
    relevant = False
    for changed in changed_files:
        stem = Path(changed).stem.removeprefix("test_")
        relevant |= any(stem in Path(target).stem or changed == target for target in targets)
    if not relevant:
        return None
    match = re.search(r"(?m)^\s*(?:=+\s*)?(\d+) passed(?:\s|$)", output)
    if not match or int(match.group(1)) <= 0:
        return None
    return VerificationRecord(
        criterion_ids=("task",),
        evidence=VerificationEvidence(kind="executable", command_operation_id=operation_id),
        workspace_fingerprint=fingerprint,
        status="passed",
    )
