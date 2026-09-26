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

ECONOMY_TOOLS = ("repo_list", "repo_search", "file_read", "edit_file", "write_file", "diff_inspect", "finish_request")


def private_path(path: str) -> bool:
    name = Path(path).name.lower()
    return name == ".env" or name.startswith(".env.") or name in {"credentials.json", "id_rsa", "id_ed25519"} or name.endswith((".pem", ".key", ".p12"))


def tool_schemas(names: tuple[str, ...] | None = None) -> tuple[dict[str, Any], ...]:
    schemas = tuple({
        "type": "function",
        "function": {
            "name": name,
            "description": {
                "repo_list": "List repository text files",
                "repo_search": "Find literal text; returned offsets can be passed to file_read. Optionally narrow relative_path.",
                "file_read": "Read up to 4000 characters and full-file SHA-256; use next_offset to read more",
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
                ) for key, typ in fields.items()} | ({"offset": {"type": "integer", "minimum": 0}} if name in {"file_read", "artifact_read", "repo_list"} else {}) | ({"limit": {"type": "integer", "minimum": 256, "maximum": 16000}} if name == "file_read" else {}) | ({"relative_path": {"type": "string"}} if name == "repo_search" else {}),
                "required": list(fields),
                "additionalProperties": False,
            },
        },
    } for name, fields in SPECS.items())
    if names is None:
        return schemas
    if "patch_apply" not in names:
        for schema in schemas:
            function = schema["function"]
            if function["name"] == "file_read":
                function["description"] = "Read text and read_id; offset/limit select a page (default 4000, max 16000). Read all pages before whole-file rewrite."
            elif function["name"] == "finish_request":
                function["description"] = "Finish with a read-only answer or an honest blocker."
    edit = {
        "type": "function", "function": {
            "name": "edit_file",
            "description": "Plan and replace exact text from a file_read. done=true finishes after this edit; false continues.",
            "parameters": {
                "type": "object", "properties": {
                    "plan": {"type": "string", "minLength": 1, "maxLength": 600, "pattern": r"\S"},
                    "read_id": {"type": "string"},
                    "old_text": {"type": "string", "minLength": 1},
                    "new_text": {"type": "string"},
                    "done": {"type": "boolean"},
                },
                "required": ["plan", "read_id", "old_text", "new_text", "done"],
                "additionalProperties": False,
            },
        },
    }
    write = {
        "type": "function", "function": {
            "name": "write_file",
            "description": "Create a new file, or rewrite a fully read file using read_id. Send complete content once; done=true finishes.",
            "parameters": {
                "type": "object", "properties": {
                    "plan": {"type": "string", "minLength": 1, "maxLength": 600, "pattern": r"\S"},
                    "relative_path": {"type": "string"},
                    "read_id": {"type": "string", "description": "Required to replace an existing file; omit for creation."},
                    "content": {"type": "string", "minLength": 1, "maxLength": 100000},
                    "done": {"type": "boolean"},
                },
                "required": ["plan", "relative_path", "content", "done"], "additionalProperties": False,
            },
        },
    }
    return tuple(schema for schema in (*schemas, edit, write) if schema["function"]["name"] in names)


class ToolDispatcher:
    def __init__(self, workspace: Workspace, artifacts: ArtifactStore, supervisor: Any, allow_commands: bool = False) -> None:
        self.workspace = workspace
        self.artifacts = artifacts
        self.supervisor = supervisor
        self.allow_commands = allow_commands
        self.results: dict[str, ToolResult] = {}
        self.reads: dict[str, tuple[str, str, int, str]] = {}

    @property
    def observed_page_count(self) -> int:
        return len({(path, sha256, offset) for path, sha256, offset, _ in self.reads.values()})

    def inspection_snapshot(self, max_chars: int = 9000) -> str:
        """Return bounded observed source for a fresh edit-only model turn."""
        blocks: list[str] = []
        size = 0
        seen: set[tuple[str, str, int]] = set()
        for read_id, (path, sha256, offset, text) in self.reads.items():
            key = (path, sha256, offset)
            if key in seen:
                continue
            seen.add(key)
            header = f"read_id={read_id} path={path} offset={offset}\n"
            available = max_chars - size - len(header)
            if available <= 0:
                break
            body = text[:available]
            blocks.append(header + body)
            size += len(header) + len(body)
        return "\n\n".join(blocks)

    async def execute(self, call: ToolCall) -> ToolResult:
        name, args = call.tool, call.arguments
        if name not in SPECS and name not in {"edit_file", "write_file"}:
            return self._fail(call, "unknown tool")
        schema = next(item["function"]["parameters"] for item in tool_schemas((name,)) if item["function"]["name"] == name)
        try:
            validate(args, schema)
            if name == "repo_list":
                prefix = args["relative_path"].rstrip("/")
                if Path(args["relative_path"]).is_absolute():
                    raise ValueError("path escapes repository")
                if prefix == ".":
                    prefix = ""
                if prefix:
                    self.workspace.resolve(prefix, allow_new=True)
                    prefix = Path(prefix).as_posix()
                paths = [path.relative_to(self.workspace.root).as_posix() for path in self.workspace._paths()]
                matches = [path for path in paths if (not prefix or path == prefix or path.startswith(prefix + "/")) and not private_path(path)]
                offset = args.get("offset", 0)
                end = offset + 60
                data = {"paths": matches[offset:end], "truncated": len(matches) > end,
                        "next_offset": end if len(matches) > end else None}
            elif name == "repo_search":
                query = args["query"]
                if not query.strip():
                    raise ValueError("query must contain text")
                prefix = args.get("relative_path", "").rstrip("/")
                if Path(args.get("relative_path", "")).is_absolute():
                    raise ValueError("path escapes repository")
                if prefix == ".":
                    prefix = ""
                if prefix:
                    self.workspace.resolve(prefix, allow_new=True)
                    prefix = Path(prefix).as_posix()
                matches = []
                searched = 0
                for path in self.workspace._paths():
                    relative = path.relative_to(self.workspace.root).as_posix()
                    if prefix and relative != prefix and not relative.startswith(prefix + "/"):
                        continue
                    if private_path(path.name):
                        continue
                    if searched >= 2000:
                        break
                    searched += 1
                    try:
                        lines = path.read_bytes().decode("utf-8").splitlines(keepends=True)
                    except (OSError, UnicodeError):
                        continue
                    offset = 0
                    for number, line in enumerate(lines, 1):
                        if query in line:
                            match_offset = offset + line.index(query)
                            matches.append({"path": relative, "line": number, "offset": max(0, match_offset - 300), "text": line[max(0, line.index(query) - 40):line.index(query) + 120].rstrip()})
                            if len(matches) >= 20:
                                break
                        offset += len(line)
                    if len(matches) >= 20:
                        break
                data = {"matches": matches, "limit_reached": len(matches) == 20}
            elif name == "file_read":
                if private_path(args["relative_path"]):
                    raise ValueError("private file content is unavailable to the model")
                path = self.workspace.resolve(args["relative_path"])
                raw = path.read_bytes()
                text = raw.decode("utf-8")
                data = {"path": args["relative_path"], "sha256": digest(raw), "total_chars": len(text),
                        **self._page(text, args.get("offset", 0), args.get("limit", 4000))}
                read_id = f"r{len(self.reads) + 1}"
                self.reads[read_id] = (path.relative_to(self.workspace.root).as_posix(), data["sha256"], data["offset"], data["text"])
                data["read_id"] = read_id
                data["fully_read"] = self._coverage(self.reads[read_id][0], data["sha256"]) >= len(text)
            elif name == "edit_file":
                if args["read_id"] not in self.reads:
                    raise ValueError("unknown read_id; read the target file first")
                path, sha256, _, page = self.reads[args["read_id"]]
                if args["old_text"] not in page:
                    raise ValueError("old_text was not in this read; read the relevant page")
                if args["old_text"] == args["new_text"]:
                    raise ValueError("replacement makes no change")
                data = self._patch([{"path": path, "expected_hash": sha256,
                                     "old_text": args["old_text"], "new_text": args["new_text"]}])
                data["done"] = args["done"]
            elif name == "write_file":
                data = self._write_file(args)
            elif name == "patch_apply":
                data = self._patch(args["edits"])
            elif name == "command_start":
                if not self.allow_commands:
                    raise ValueError("command execution is disabled for this workspace-locked session")
                result = await self.supervisor.run(args["command"])
                data = result
            elif name == "diff_inspect":
                changes = self.workspace.changes()
                data = {"changed_files": changes.changed_files, "attributable_files": changes.attributable_files, "external_files": changes.external_files, "ambiguous_files": changes.ambiguous_files, "patch": self.workspace.patch_text()[:12000]}
            elif name == "artifact_read":
                data = self._page(self.artifacts.read(args["artifact_id"]).decode("utf-8", "replace"), args.get("offset", 0))
            else:
                data = {"summary": args["summary"]}
            result = ToolResult(operation_id=call.operation_id, status=OperationStatus.succeeded, summary=name, data=data)
        except (ValueError, OSError, UnicodeError, KeyError, TypeError, ValidationError) as exc:
            result = self._fail(call, str(exc))
        self.results[result.operation_id] = result
        return result

    @staticmethod
    def _page(text: str, offset: int, limit: int = 4000) -> dict:
        if offset > len(text):
            raise ValueError("offset exceeds file length")
        end = min(offset + limit, len(text))
        return {"text": text[offset:end], "offset": offset, "next_offset": end if end < len(text) else None, "truncated": end < len(text)}

    def _coverage(self, path: str, sha256: str) -> int:
        end = 0
        for offset, text in sorted((offset, text) for p, h, offset, text in self.reads.values() if p == path and h == sha256):
            if offset > end:
                break
            end = max(end, offset + len(text))
        return end

    def _write_file(self, args: dict) -> dict:
        relative = args["relative_path"]
        if private_path(relative):
            raise ValueError("private file edits are unavailable")
        path = self.workspace.resolve(relative, allow_new=True)
        relative = path.relative_to(self.workspace.root).as_posix()
        content = args["content"].encode("utf-8")
        if path.exists():
            read_id = args.get("read_id")
            if read_id not in self.reads:
                raise ValueError("existing file requires read_id; read it before rewriting")
            read_path, sha256, _, _ = self.reads[read_id]
            if read_path != relative:
                raise ValueError("read_id belongs to another file")
            raw = path.read_bytes()
            if digest(raw) != sha256:
                raise ValueError("stale read; reread the changed file")
            original = raw.decode("utf-8")
            if self._coverage(relative, sha256) < len(original):
                raise ValueError(f"read the remaining file before rewriting; next unread offset={self._coverage(relative, sha256)}")
            if raw == content:
                raise ValueError("replacement makes no change")
            result = self._patch([{"path": relative, "expected_hash": sha256,
                                   "old_text": original, "new_text": args["content"]}])
        else:
            if args.get("read_id"):
                raise ValueError("file was removed after reading; refusing to recreate it")
            path.parent.mkdir(parents=True, exist_ok=True)
            path = self.workspace.resolve(relative, allow_new=True)
            # Link an already written temporary file exclusively, never overwrite
            # a concurrently created target. Both paths are inside the workspace.
            fd, temp = tempfile.mkstemp(prefix=".ion-", dir=path.parent)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(content)
                os.link(temp, path)
                self.workspace.record_write(relative, None, digest(content), b"", content)
            finally:
                Path(temp).unlink(missing_ok=True)
            result = {"changed_files": [relative]}
        return {**result, "done": args["done"]}

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
            if (not old and text) or text.count(old) != 1:
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
