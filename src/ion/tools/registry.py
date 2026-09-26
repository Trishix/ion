from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import validate
from jsonschema.exceptions import ValidationError

from ion.artifacts import ArtifactStore
from ion.contracts import OperationStatus, ToolCall, ToolResult
from ion.workspace import Workspace, digest


SPECS: dict[str, dict[str, Any]] = {
    "repo_list": {"relative_path": "string"},
    "repo_search": {"query": "string"},
    "file_read": {"relative_path": "string"},
    "patch_apply": {"edits": "array"},
    "command_start": {"command": "string"},
    "diff_inspect": {},
    "artifact_read": {"artifact_id": "string"},
    "finish_request": {"summary": "string"},
}


def private_path(path: str) -> bool:
    name = Path(path).name.lower()
    return name == ".env" or name.startswith(".env.") or name in {"credentials.json", "id_rsa", "id_ed25519"} or name.endswith((".pem", ".key", ".p12"))


def tool_schemas() -> tuple[dict[str, Any], ...]:
    return tuple({
        "type": "function",
        "function": {
            "name": name,
            "description": {
                "repo_list": "List repository text files",
                "repo_search": "Search repository text",
                "file_read": "Read a text file and its SHA-256 hash",
                "patch_apply": "Replace exact old_text with new_text, requiring expected_hash for each file",
                "command_start": "Run a bounded repository command",
                "diff_inspect": "Inspect changes since task start",
                "artifact_read": "Read a retained tool artifact",
                "finish_request": "Request verification and final report",
            }[name],
            "parameters": {
                "type": "object",
                "properties": {key: (
                    {"type": "array", "minItems": 1, "items": {"type": "object", "properties": {
                        "path": {"type": "string"}, "expected_hash": {"type": "string"},
                        "old_text": {"type": "string"}, "new_text": {"type": "string"},
                    }, "required": ["path", "expected_hash", "old_text", "new_text"], "additionalProperties": False}}
                    if name == "patch_apply" and key == "edits" else {"type": typ}
                ) for key, typ in fields.items()},
                "required": list(fields),
                "additionalProperties": False,
            },
        },
    } for name, fields in SPECS.items())


class ToolDispatcher:
    def __init__(self, workspace: Workspace, artifacts: ArtifactStore, supervisor: Any) -> None:
        self.workspace = workspace
        self.artifacts = artifacts
        self.supervisor = supervisor
        self.results: dict[str, ToolResult] = {}

    async def execute(self, call: ToolCall) -> ToolResult:
        name, args = call.tool, call.arguments
        if name not in SPECS:
            return self._fail(call, "unknown tool")
        schema = next(item["function"]["parameters"] for item in tool_schemas() if item["function"]["name"] == name)
        try:
            validate(args, schema)
            if name == "repo_list":
                prefix = args["relative_path"].strip("/")
                if prefix:
                    self.workspace.resolve(prefix, allow_new=True)
                paths = [path.relative_to(self.workspace.root).as_posix() for path in self.workspace._paths()]
                data = {"paths": [path for path in paths if path.startswith(prefix)][:200]}
            elif name == "repo_search":
                query = args["query"]
                matches = []
                for path in self.workspace._paths()[:2000]:
                    if private_path(path.name):
                        continue
                    try:
                        lines = path.read_text(encoding="utf-8").splitlines()
                    except (OSError, UnicodeError):
                        continue
                    for number, line in enumerate(lines, 1):
                        if query in line:
                            matches.append({"path": path.relative_to(self.workspace.root).as_posix(), "line": number, "text": line[:500]})
                            if len(matches) >= 100:
                                break
                    if len(matches) >= 100:
                        break
                data = {"matches": matches}
            elif name == "file_read":
                if private_path(args["relative_path"]):
                    raise ValueError("private file content is unavailable to the model")
                path = self.workspace.resolve(args["relative_path"])
                raw = path.read_bytes()
                data = {"path": args["relative_path"], "sha256": digest(raw), "text": raw.decode("utf-8")[:12000]}
            elif name == "patch_apply":
                data = self._patch(args["edits"])
            elif name == "command_start":
                result = await self.supervisor.run(args["command"])
                data = result
            elif name == "diff_inspect":
                changes = self.workspace.changes()
                data = {"changed_files": changes.changed_files, "attributable_files": changes.attributable_files, "external_files": changes.external_files, "ambiguous_files": changes.ambiguous_files, "patch": self.workspace.patch_text()[:12000]}
            elif name == "artifact_read":
                data = {"text": self.artifacts.read(args["artifact_id"]).decode("utf-8", "replace")[:12000]}
            else:
                data = {"summary": args["summary"]}
            result = ToolResult(operation_id=call.operation_id, status=OperationStatus.succeeded, summary=name, data=data)
        except (ValueError, OSError, UnicodeError, KeyError, TypeError, ValidationError) as exc:
            result = self._fail(call, str(exc))
        self.results[result.operation_id] = result
        return result

    def _fail(self, call: ToolCall, reason: str) -> ToolResult:
        result = ToolResult(operation_id=call.operation_id, status=OperationStatus.failed, summary="tool failed", error=reason)
        self.results[result.operation_id] = result
        return result

    def _patch(self, edits: list[dict[str, Any]]) -> dict[str, Any]:
        if not isinstance(edits, list) or not edits:
            raise ValueError("edits must be a nonempty array")
        prepared = []
        seen = set()
        for edit in edits:
            if set(edit) != {"path", "expected_hash", "old_text", "new_text"}:
                raise ValueError("invalid patch edit fields")
            relative = edit["path"]
            if private_path(relative):
                raise ValueError("private file edits are unavailable")
            if relative in seen:
                raise ValueError("duplicate patch path")
            seen.add(relative)
            path = self.workspace.resolve(relative)
            raw = path.read_bytes()
            if digest(raw) != edit["expected_hash"]:
                raise ValueError("stale patch input")
            text = raw.decode("utf-8")
            old = edit["old_text"]
            if not old or text.count(old) != 1:
                raise ValueError("old_text must match exactly once")
            replacement = text.replace(old, edit["new_text"], 1).encode("utf-8")
            prepared.append((relative, path, raw, replacement))
        temp_paths = []
        try:
            for _, path, _, replacement in prepared:
                fd, name = tempfile.mkstemp(prefix=".ion-", dir=path.parent)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(replacement)
                os.chmod(name, path.stat().st_mode)
                temp_paths.append(Path(name))
            for _, path, old, _ in prepared:
                if digest(path.read_bytes()) != digest(old):
                    raise ValueError("file changed during patch")
            for (relative, path, old, replacement), temp in zip(prepared, temp_paths):
                temp.replace(path)
                self.workspace.record_write(relative, digest(old), digest(replacement), old, replacement)
        finally:
            for path in temp_paths:
                path.unlink(missing_ok=True)
        return {"changed_files": [item[0] for item in prepared]}
