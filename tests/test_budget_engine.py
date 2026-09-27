import json
from pathlib import Path

import pytest

from ion.artifacts import ArtifactStore
from ion.config import load_config
from ion.context import ContextManager
from ion.contracts import ModelEvent, TaskSpec, ToolResult
from ion.engine import Engine
from ion.processes import CommandSupervisor
from ion.providers.scripted import ScriptedProvider
from ion.tools.registry import ToolDispatcher
from ion.workspace import Workspace


def _engine(tmp_path, provider, *, tokens=24000, input_budget=6000, files=None, economy_fields=None, allow_commands=False):
    repo = tmp_path / "repo"
    repo.mkdir()
    for name, content in (files or {}).items():
        (repo / name).write_text(content)
    workspace = Workspace.capture(repo)
    artifacts = ArtifactStore(tmp_path / "artifacts")
    dispatcher = ToolDispatcher(workspace, artifacts, CommandSupervisor(workspace, artifacts), allow_commands=allow_commands)
    config = load_config(Path(__file__).resolve().parents[1] / "ion.toml")
    config = config.model_copy(update={"economy": config.economy.model_copy(update={"max_total_tokens": tokens, **(economy_fields or {})})})
    profile = config.profiles[config.default_profile].copy()
    profile["input_budget_tokens"] = input_budget
    config = config.model_copy(update={"profiles": {**config.profiles, config.default_profile: profile}})
    return Engine(config, provider, dispatcher), repo


@pytest.mark.asyncio
async def test_engine_reports_context_overflow_without_dispatch(tmp_path):
    provider = ScriptedProvider([])
    engine, repo = _engine(tmp_path, provider, input_budget=2400)
    context = ContextManager()

    def build_with_required_result(*args, **kwargs):
        history = [*args[3],
                   {"role": "assistant", "content": None, "tool_calls": [{"id": "latest", "type": "function", "function": {"name": "file_read", "arguments": "{}"}}]},
                   {"role": "tool", "tool_call_id": "latest", "content": json.dumps({"status": "succeeded", "data": {"text": "x" * 20000}})}]
        return context.build(*args[:3], history, *args[4:], **kwargs)

    engine.context.build = build_with_required_result
    result = await engine.run(TaskSpec(text="Inspect project", repo_path=str(repo), profile_name=engine.config.default_profile))

    assert len(provider.requests) == 0
    assert result.outcome == "blocked"
    assert result.error_category == "context_overflow"
    assert result.request_dispatched is False
    assert "no model request was sent" in result.summary.lower()
    assert result.budget is not None


@pytest.mark.asyncio
async def test_small_final_action_uses_dynamic_output_cap(tmp_path):
    provider = ScriptedProvider([
        [ModelEvent(kind="tool_call", tool="file_read", arguments={"relative_path": "note.txt"}, call_id="read"),
         ModelEvent(kind="usage", usage={"prompt_tokens": 4300, "completion_tokens": 10}), ModelEvent(kind="completed")],
        [ModelEvent(kind="tool_call", tool="finish_request", arguments={"summary": "Inspected note"}, call_id="finish"),
         ModelEvent(kind="completed")],
    ])
    engine, repo = _engine(tmp_path, provider, tokens=6000, files={"note.txt": "A short note.\n"})
    result = await engine.run(TaskSpec(text="Inspect project", repo_path=str(repo), profile_name=engine.config.default_profile))

    assert len(provider.requests) == 2, result
    assert provider.requests[1].max_output_tokens < 1024
    assert result.summary == "Inspected note"
    assert result.request_dispatched is True
    assert result.budget is not None


@pytest.mark.asyncio
async def test_configured_inspection_tier_controls_request_cap(tmp_path):
    provider = ScriptedProvider([[ModelEvent(kind="tool_call", tool="file_read",
                                             arguments={"relative_path": "note.txt"}, call_id="read"),
                                  ModelEvent(kind="completed")],
                                 [ModelEvent(kind="tool_call", tool="finish_request",
                                             arguments={"summary": "Inspected"}, call_id="finish"),
                                  ModelEvent(kind="completed")]])
    engine, repo = _engine(tmp_path, provider, files={"note.txt": "small"},
                           economy_fields={"inspect_output_tokens": 768})
    await engine.run(TaskSpec(text="Inspect project", repo_path=str(repo), profile_name=engine.config.default_profile))
    assert provider.requests[0].max_output_tokens == 768


@pytest.mark.asyncio
async def test_incomplete_edit_keeps_edit_tools_available(tmp_path):
    provider = ScriptedProvider([
        [ModelEvent(kind="tool_call", tool="file_read", arguments={"relative_path": "a.txt"}, call_id="read"), ModelEvent(kind="completed")],
        [ModelEvent(kind="tool_call", tool="edit_file", arguments={"plan": "Update first note", "read_id": "r1", "old_text": "old", "new_text": "new", "done": False}, call_id="edit"), ModelEvent(kind="completed")],
        [ModelEvent(kind="tool_call", tool="file_read", arguments={"relative_path": "b.txt"}, call_id="next"), ModelEvent(kind="completed")],
        [ModelEvent(kind="tool_call", tool="finish_request", arguments={"summary": "One edit applied"}, call_id="finish"), ModelEvent(kind="completed")],
    ])
    engine, repo = _engine(tmp_path, provider, files={"a.txt": "old", "b.txt": "other"}, allow_commands=True)
    await engine.run(TaskSpec(text="Change project notes", repo_path=str(repo), profile_name=engine.config.default_profile))
    assert len(provider.requests) >= 3
    assert (repo / "a.txt").read_text() == "new"
    assert "file_read" in {schema["function"]["name"] for schema in provider.requests[2].tools}


@pytest.mark.asyncio
async def test_truncated_tool_call_is_not_executed(tmp_path):
    from ion.workspace import digest

    patch = {"edits": [{"path": "a.txt", "expected_hash": digest(b"old"), "old_text": "old", "new_text": "new"}]}
    provider = ScriptedProvider([
        [ModelEvent(kind="tool_call", tool="patch_apply", arguments=patch, call_id="partial"),
         ModelEvent(kind="completed", finish_reason="length")],
        [ModelEvent(kind="tool_call", tool="patch_apply", arguments=patch, call_id="complete"), ModelEvent(kind="completed")],
        [ModelEvent(kind="tool_call", tool="finish_request", arguments={"summary": "Updated"}, call_id="finish"), ModelEvent(kind="completed")],
    ])
    engine, repo = _engine(tmp_path, provider, files={"a.txt": "old"})
    result = await engine.run(TaskSpec(text="Fix a.txt", repo_path=str(repo), profile_name=engine.config.default_profile))
    assert len(provider.requests) >= 2
    assert (repo / "a.txt").read_text() == "new"
    assert result.changed_files == ("a.txt",)


@pytest.mark.asyncio
async def test_provider_rate_limit_keeps_its_error_category(tmp_path):
    provider = ScriptedProvider([[ModelEvent(kind="error", error="provider rate limit", retry_after_seconds=31)]])
    engine, repo = _engine(tmp_path, provider)
    result = await engine.run(TaskSpec(text="Inspect project", repo_path=str(repo), profile_name=engine.config.default_profile))
    assert result.outcome == "failed"
    assert result.error_category == "provider_rate_limit"
    assert result.request_dispatched is True
    assert len(provider.requests) == 1


def test_tool_preview_respects_configured_maximum():
    response = Engine._tool_response(ToolResult(operation_id="op", status="succeeded", summary="read",
                                               data={"output": "x" * 1000}), max_chars=256)
    preview = json.loads(response)["data"]["output"]
    assert len(preview) <= 256
    assert "output shortened" in preview
