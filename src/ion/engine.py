from __future__ import annotations

import asyncio
import json
from pathlib import Path

from ion.budget import BudgetLedger
from ion.config import AppConfig, resolve_profile
from ion.context import ContextManager
from ion.contracts import EngineEvent, ModelEvent, ModelRequest, OperationStatus, Outcome, Phase, TaskResult, TaskSpec, ToolCall, VerificationRecord
from ion.gateway import ModelGateway, profile_digest
from ion.instructions import InstructionResolver
from ion.protocols import FinishAction, ToolAction, parse_action
from ion.tools.registry import ToolDispatcher, tool_schemas
from ion.verification import CompletionGate, observe_pytest


class Engine:
    def __init__(self, config: AppConfig, gateway: ModelGateway, dispatcher: ToolDispatcher, profile_override=None) -> None:
        self.config = config
        self.gateway = gateway
        self.dispatcher = dispatcher
        self.profile_override = profile_override
        self.budget = BudgetLedger()
        self.context = ContextManager()
        self.queue: asyncio.Queue[EngineEvent] = asyncio.Queue()
        self.cancelled = False
        self.pending_steering: list[str] = []
        self.applied_steering: list[str] = []

    async def events(self):
        while True:
            event = await self.queue.get()
            yield event
            if event.phase == Phase.finalize:
                break

    async def cancel(self) -> None:
        self.cancelled = True
        await self.dispatcher.supervisor.close()

    async def steer(self, instruction: str) -> None:
        if not instruction.strip():
            raise ValueError("steering instruction cannot be blank")
        self.pending_steering.append(instruction.strip())
        await self._emit(Phase.intake, f"User steering queued: {instruction.strip()[:200]}")

    async def _emit(self, phase: Phase, message: str) -> None:
        await self.queue.put(EngineEvent(phase=phase, message=message))

    async def run(self, task: TaskSpec) -> TaskResult:
        profile = self.profile_override or resolve_profile(self.config, task.profile_name, task.mode)
        workspace = self.dispatcher.workspace
        if Path(task.repo_path).resolve() != workspace.root:
            raise ValueError("task repository does not match workspace")
        instructions = InstructionResolver().resolve(workspace.root, [])
        instruction_text = "\n".join(f"{item.path} ({item.sha256}):\n{item.text}" for item in instructions)
        history: list[dict] = [{"role": "user", "content": task.text}]
        records: list[VerificationRecord] = []
        summary = "No final result supplied"
        outcome = Outcome.unverified
        rate_limit_retries = 0
        reported_dropped_turns = 0
        await self._emit(Phase.intake, "Task accepted")
        try:
            for _ in range(100):
                if self.cancelled:
                    outcome = Outcome.cancelled
                    break
                if self.pending_steering:
                    additions = self.pending_steering[:]
                    self.pending_steering.clear()
                    self.applied_steering.extend(additions)
                    history.append({"role": "user", "content": "User steering: " + "\n".join(additions)})
                self.budget.admit(Phase.act)
                packet = self.context.build(task, profile, Phase.act, history, instruction_text, tuple(self.applied_steering))
                if packet.dropped_turns > reported_dropped_turns:
                    reported_dropped_turns = packet.dropped_turns
                    await self._emit(Phase.act, f"Context trimmed: {reported_dropped_turns} older tool turns omitted")
                request = ModelRequest(messages=packet.messages, tools=tool_schemas() if profile.tool_protocol == "native" else (), max_output_tokens=packet.max_output_tokens, profile_digest=profile_digest(profile))
                text_parts: list[str] = []
                calls: list[ModelEvent] = []
                error = None
                retry_after_seconds: float | None = None
                async for event in self.gateway.generate(request):
                    if event.kind == "text_delta":
                        text_parts.append(event.text)
                    elif event.kind == "tool_call":
                        calls.append(event)
                    elif event.kind == "error":
                        error = event.error or "provider error"
                        retry_after_seconds = event.retry_after_seconds
                if error:
                    if error == "provider rate limit" and rate_limit_retries < 2:
                        retry_seconds = retry_after_seconds if retry_after_seconds is not None else float(rate_limit_retries + 1)
                        if retry_seconds > 30:
                            summary = f"Provider rate limit; retry after about {int(retry_seconds)} seconds"
                            outcome = Outcome.failed
                            break
                        rate_limit_retries += 1
                        delay = max(1, int(retry_seconds + 0.999))
                        await self._emit(Phase.act, f"Provider rate limit; retrying in {delay}s")
                        await asyncio.sleep(delay)
                        continue
                    summary = error
                    outcome = Outcome.failed
                    break
                rate_limit_retries = 0
                content = "".join(text_parts)
                if profile.tool_protocol == "structured_json":
                    try:
                        action = parse_action(content)
                        if isinstance(action, ToolAction):
                            calls.append(ModelEvent(kind="tool_call", tool=action.tool, arguments=action.arguments, call_id="structured"))
                        else:
                            summary = action.summary
                    except ValueError:
                        history.append({"role": "assistant", "content": content})
                        history.append({"role": "user", "content": "Return exactly one valid JSON action object."})
                        continue
                if calls:
                    if len(calls) > 1 and any(event.tool == "finish_request" for event in calls):
                        summary = "finish_request must be the only tool call in its response"
                        outcome = Outcome.blocked
                        break
                    finish_requested = False
                    assistant: dict = {"role": "assistant", "content": content or None}
                    if profile.tool_protocol == "native":
                        assistant["tool_calls"] = [{"id": call.call_id, "type": "function", "function": {"name": call.tool, "arguments": json.dumps(call.arguments)}} for call in calls]
                    history.append(assistant)
                    for event in calls:
                        call = ToolCall(task_id=task.task_id, tool=event.tool or "", arguments=event.arguments or {})
                        await self._emit(Phase.act, f"{call.tool} requested")
                        if call.tool == "finish_request":
                            summary = str(call.arguments.get("summary", content))
                            finish_requested = True
                            if self.pending_steering:
                                result = await self.dispatcher.execute(call)
                                response = json.dumps(result.model_dump(mode="json"), ensure_ascii=False)
                                if profile.tool_protocol == "native":
                                    history.append({"role": "tool", "tool_call_id": event.call_id, "content": response[:12000]})
                                else:
                                    history.append({"role": "user", "content": f"Tool result: {response[:12000]}"})
                            break
                        result = await self.dispatcher.execute(call)
                        if call.tool == "command_start" and result.status == OperationStatus.succeeded:
                            data = result.data
                            record = observe_pytest(str(call.arguments.get("command", "")), str(data.get("output", "")), int(data.get("exit_code") or 0), call.operation_id, workspace.fingerprint(), workspace.changes().changed_files)
                            if record:
                                records.append(record)
                        response = json.dumps(result.model_dump(mode="json"), ensure_ascii=False)
                        if profile.tool_protocol == "native":
                            history.append({"role": "tool", "tool_call_id": event.call_id, "content": response[:12000]})
                        else:
                            history.append({"role": "user", "content": f"Tool result: {response[:12000]}"})
                    if finish_requested:
                        if self.pending_steering:
                            continue
                        break
                else:
                    summary = summary if summary != "No final result supplied" else content
                    if self.pending_steering:
                        history.append({"role": "assistant", "content": content})
                        continue
                    break
            else:
                outcome = Outcome.budget_exhausted
        except (RuntimeError, ValueError) as exc:
            summary = str(exc)
            outcome = Outcome.budget_exhausted if "budget" in summary or "reserve" in summary else Outcome.blocked
        finally:
            await self.dispatcher.supervisor.close()
        await self._emit(Phase.verify, "Checking final workspace")
        fingerprint = workspace.fingerprint()
        changes = workspace.changes()
        patch = workspace.patch_text()
        patch_artifact = self.dispatcher.artifacts.put(patch.encode(), "ion_patch") if patch else None
        if outcome == Outcome.unverified:
            outcome = CompletionGate().decide(changes, records, fingerprint)
        result = TaskResult(task_id=task.task_id, outcome=outcome, summary=summary, changed_files=changes.changed_files, patch_artifact_id=patch_artifact.artifact_id if patch_artifact else None, verification_ids=tuple(record.verification_id for record in records), limitations=("Minimal verification supports pytest output only",) if outcome != Outcome.verified else (), final_workspace_fingerprint=fingerprint)
        await self._emit(Phase.finalize, f"{outcome.value}: {summary}")
        return result
