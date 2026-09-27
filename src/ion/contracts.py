from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
import re


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Phase(StrEnum):
    intake = "intake"
    inspect = "inspect"
    plan = "plan"
    act = "act"
    verify = "verify"
    finalize = "finalize"


class Outcome(StrEnum):
    verified = "verified"
    unverified = "unverified"
    blocked = "blocked"
    budget_exhausted = "budget_exhausted"
    failed = "failed"
    cancelled = "cancelled"


class OperationStatus(StrEnum):
    prepared = "prepared"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"
    unknown = "unknown"


class ModelProfile(StrictModel):
    provider: str
    endpoint: str
    model_id: str
    api_key_env: str = "AI_API_KEY"
    protocol: Literal["openai_chat"] = "openai_chat"
    tool_protocol: Literal["native", "structured_json"] = "native"
    text_only: Literal[True] = True
    locked: bool = False
    context_window: int = Field(gt=1024)
    max_output_tokens: int = Field(gt=0)

    @field_validator("api_key_env")
    @classmethod
    def valid_key_name(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*_API_KEY", value):
            raise ValueError("api_key_env must name an environment variable ending in _API_KEY")
        return value

    @model_validator(mode="after")
    def check_limits(self) -> ModelProfile:
        if self.max_output_tokens >= self.context_window:
            raise ValueError("max_output_tokens must be below context_window")
        return self


class TaskSpec(StrictModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    text: str
    repo_path: str
    profile_name: str
    mode: Literal["product", "evaluation"] = "product"
    criteria: tuple[str, ...] = ()

    @field_validator("text", "repo_path", "profile_name")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be blank")
        return value


class ToolCall(StrictModel):
    operation_id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    tool: str
    arguments: dict[str, Any]
    status: OperationStatus = OperationStatus.prepared


class ToolResult(StrictModel):
    operation_id: str
    status: OperationStatus
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    artifact_ids: tuple[str, ...] = ()
    error: str | None = None
    duration_ms: int = 0
    truncated: bool = False
    lossy: bool = False


class ArtifactRef(StrictModel):
    artifact_id: str
    kind: str
    relative_store_path: str
    sha256: str
    byte_count: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    complete: bool = True
    redaction_applied: bool = False


class VerificationEvidence(StrictModel):
    kind: Literal["executable", "observation", "static"]
    command_operation_id: str | None = None
    source_operation_ids: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    artifact_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def check_source(self) -> VerificationEvidence:
        if self.kind == "executable" and not self.command_operation_id:
            raise ValueError("executable evidence requires a command")
        if self.kind != "executable" and not (self.source_operation_ids or self.source_refs or self.artifact_ids):
            raise ValueError("evidence requires a source")
        return self


class VerificationRecord(StrictModel):
    verification_id: str = Field(default_factory=lambda: str(uuid4()))
    criterion_ids: tuple[str, ...]
    evidence: VerificationEvidence
    workspace_fingerprint: str
    status: Literal["passed", "failed", "unavailable", "invalidated"]
    limitations: tuple[str, ...] = ()


class TaskResult(StrictModel):
    schema_version: Literal[1] = 1
    task_id: str
    outcome: Outcome
    summary: str
    changed_files: tuple[str, ...] = ()
    patch_artifact_id: str | None = None
    verification_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    final_workspace_fingerprint: str | None = None


class ModelRequest(StrictModel):
    messages: tuple[dict[str, Any], ...]
    tools: tuple[dict[str, Any], ...] = ()
    max_output_tokens: int
    profile_digest: str


class ModelEvent(StrictModel):
    kind: Literal["text_delta", "tool_call", "usage", "completed", "error"]
    text: str = ""
    tool: str | None = None
    arguments: dict[str, Any] | None = None
    call_id: str | None = None
    usage: dict[str, int] | None = None
    error: str | None = None
    retry_after_seconds: float | None = Field(default=None, ge=0)


class ModelInfo(StrictModel):
    model_id: str
    context_window: int | None = None
    max_output_tokens: int | None = None
    text_only: bool | None = None
    supports_tools: bool | None = None
    free: bool | None = None
    available: bool = True


class ProbeResult(StrictModel):
    model_id: str
    text_ok: bool
    tools_ok: bool
    protocol: str
    profile_digest: str


class EngineEvent(StrictModel):
    phase: Phase
    message: str
