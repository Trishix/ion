# Interfaces, data contracts, and defaults

Status: normative v1 design, not an implemented API. This document is the single owner of shared names, states, defaults, and schema rules.

## TUI and launch contract

`make run` launches the TUI. All user-facing task input, repository selection, session resume, inspection, memory management, and task controls are performed in that TUI. The evaluator supplies the task through the TUI according to the official protocol. The invocation directory is the default target repository; show and confirm the target before the first mutation.

The TUI provides doctor/configuration checks and a visible, auditable route to list or forget remembered knowledge. Forgetting tombstones the knowledge record and invalidates dependent retrieval/profile caches; it is not source-data deletion. Future artifact purge/export controls require their own explicit design.

`make run` always launches the TUI and fails clearly with an actionable terminal requirement if stdin/stdout are not interactive; it must never switch to another task protocol. `ION_REPO` supplies an optional target path to the Makefile launcher; without it the TUI asks for a path. Until OPEN-03 is resolved, the TUI's text-entry/paste and repository-selection flow is the development adapter, not a claim about the official evaluator's exact task-delivery mechanics.

## Session service

The TUI calls a Python client over a permission-restricted Unix domain socket owned by the session engine. This socket is private implementation IPC, not a supported public API or alternate interface. One background engine process owns each session; it outlives TUI disconnects. Write admission requires both a per-workspace advisory lock and a durable WorkspaceOwnership check. A released OS lock alone does not prove that an old command stopped. Separate Git worktrees are distinct workspaces; shared repository knowledge uses short database transactions.

Before any new or resumed session receives write authority, acquire the workspace lock and inspect the private ownership registry. An active/recovery-required claim from an exited engine requires reconciling or terminating all its surviving commands and resolving unknown mutations first. Never bypass recovery by creating a new session. Persist the new owner before dispatch; mark ownership clean only after owned processes have stopped and operations have settled.

Requests have `schema_version=1`, `request_id`, `method`, and `params`. Responses echo request_id and contain result or a structured error. Mutating control requests are deduplicated by request_id within the session. IPC frames are JSONL with a maximum of 1 MiB; large content travels as artifact references or bounded pages.

| Method | Input | Result |
| --- | --- | --- |
| start | TaskSpec | session_id |
| steer | session_id, text, request_id | recorded event sequence |
| pause | session_id, request_id | acknowledgement; paused is confirmed by state event |
| resume | session_id, request_id | acknowledgement or reconciliation blocker |
| cancel | session_id, request_id | acknowledgement; final outcome follows cleanup |
| inspect | session_id | state snapshot and last_seq |
| subscribe | session_id, after_seq | durable event replay followed by newly committed events |
| get_result | session_id | TaskResult or not_finished |

Replay and live attachment must be race-free: buffer new committed events while catching up, deduplicate by sequence, then continue. Token deltas and transient progress may use a separate live channel; they have no cursor or replay guarantee. A reconnecting client obtains an authoritative snapshot and durable events, not assumptions from missing live fragments.

## Canonical states

| Type | Values and meaning |
| --- | --- |
| ExecutionStatus | queued, running, paused, waiting, finished |
| Phase | intake, inspect, plan, act, verify, finalize |
| Outcome | verified, unverified, blocked, budget_exhausted, failed, cancelled |
| OperationStatus | prepared, running, succeeded, failed, cancelled, unknown |
| CriterionStatus | pending, satisfied, unsatisfied, unavailable |
| MemoryStatus | active, stale, superseded, expired, forgotten |
| EvidenceKind | observed, user_asserted, hypothesis, derived |
| ErrorCategory | validation, policy, stale_input, interaction_required, timeout, cancelled, provider_transient, provider_fatal, context_overflow, storage, reconciliation_required, budget |

Outcome is null unless execution_status is finished. Tool success is not task verification. A waiting task has a reason and deadline, not a success outcome. Hypotheses may be active memory but are never presented as observed facts.

## Shared records

UUIDs identify records; timestamps are UTC. Hashes are SHA-256. Paths in task evidence are repository-relative where possible; external managed artifacts use opaque IDs, never arbitrary model-supplied host paths.

| Record | Required fields and constraints |
| --- | --- |
| TaskSpec | task_id, text, repo_path, profile_name, mode (product/evaluation), criteria; original text preserved verbatim |
| AcceptanceCriterion | criterion_id, description, origin (user/agent/organizer), required, verification_kind, status, evidence_ids; agent proposals are auditable |
| TaskState | task_id, session_id, execution_status, phase, outcome, criteria, amendments, effective_constraints, amendment_version, plan_items, active_hypotheses, failed_approaches, next_action, pending_operations, workspace_baseline_id, profile_digest, budget_snapshot, last_seq |
| TaskAmendment | amendment_id, seq, original_text, source_event_id, superseded_amendment_ids, affected_criterion_ids; preserve later user constraints verbatim and fold them into effective_constraints independently of model summaries |
| WorkspaceOwnership | workspace_id, owner_session_id, engine_identity, status (active/recovery_required/clean), pending_operation_refs; durable admission record, not a lease that expires into permission |
| WorkspaceChange | change_id, operation_id (nullable), path, before_hash, after_hash, before_artifact_id, after_artifact_id, attribution (ion/external/ambiguous); record deltas, not just touched paths |
| PlanItem | item_id, description, depends_on, progress (pending/in_progress/done/blocked), evidence_ids; progress does not certify task success |
| SessionEvent | schema_version, event_id, session_id, seq, timestamp, type, payload; unique session_id/seq; append-only during normal operation |
| ToolCall | operation_id, task_id, tool, arguments, capabilities, workspace_version, deadline, status; intent committed before dispatch |
| ToolResult | operation_id, status, summary, data, artifact_ids, error, duration_ms, truncated, lossy; structured success/failure independent of display text |
| ArtifactRef | artifact_id, kind, relative_store_path, sha256, byte_count, created_at, complete, redaction_applied; no credentials |
| MemoryRecord | memory_id, scope, fact_key, text, evidence_kind, status, source_refs, supporting_hashes, observed_at, valid_from, valid_until, supersedes_id, extraction_version |
| ContextCheckpoint | checkpoint_id, session_id, through_seq, structured_state_version, amendment_version, constraints_digest, summary, recent_event_refs, pinned_evidence_refs, model_profile_digest, created_at |
| VerificationEvidence | kind (executable/observation/static), command_operation_id (nullable), source_operation_ids, source_refs, artifact_ids; kind-specific validation below |
| VerificationRecord | verification_id, criterion_ids, evidence (VerificationEvidence), workspace_fingerprint, environment_fingerprint, baseline_ref, status (passed/failed/unavailable/invalidated), limitations |
| TaskResult | schema_version, task_id, session_id, outcome, summary, patch_artifact_id, patch_attribution (ion/workspace_candidate/none), workspace_delta_artifact_id, external_change_paths, ambiguous_change_paths, changed_files, criteria, verification_ids, usage, limitations, next_steps, final_workspace_fingerprint |

Executable evidence requires a settled command_operation_id and retained test/behavior output. Observation evidence requires source_operation_ids plus artifacts or source references identifying a reproducible observation; command_operation_id is optional only when no command produced it. Static evidence requires cited path/range/hash or immutable artifact references and corresponding read/inspection operations; command_operation_id may be null. No kind accepts a model assertion without supporting observations. Unavailable checks record their reason and attempted sources rather than inventing a successful command.

source_refs identify source event/artifact, file plus range/hash, or explicit user statement. Memory relationships are stored separately as source_id, target_id, relation (supersedes/extends/derived_from); relationships must remain inside authorized scopes. Generated summaries and user-facing reports are not primary verification evidence.

## Logical storage schema

Use a per-session SQLite database for events, task projections, operations, criteria, verification, checkpoints, request deduplication, and artifact metadata. The engine is its sole writer. Event insertion and state projection updates share one transaction; notification occurs only after commit.

A per-repository SQLite knowledge database owns memory records, supporting sources, relationships, tombstones, and an FTS5 index. Separate sessions use short serialized SQLite write transactions; retry contention within deadline. FTS5 is checked during setup/doctor. A missing FTS5 capability is a setup error, not silent loss of retrieval.

A private ownership.sqlite registry at the Ion data root records WorkspaceOwnership across sessions. Its short transactions run under the workspace admission lock. It is not atomically committed with session databases: conservative active claims persist through crashes, and admission cross-checks referenced session journals before declaring an owner clean. Missing/corrupt ownership records for an existing workspace require reconciliation rather than optimistic write access.

Filesystem blobs live under the private Ion data directory. Write artifact to a temporary sibling, flush and atomically rename, then commit its metadata/event. Recovery may collect unreferenced blobs; a missing referenced blob is an integrity error. Filesystem changes in the target repository cannot share the SQLite transaction, which is why unknown operation outcomes exist.

Default data root is `$XDG_DATA_HOME/ion`, or `~/.local/share/ion` when unset. Override with `ION_DATA_DIR`. Use owner-only directories/files where supported. Never place the database in the target repository by default.

Repository identity is a generated ID mapped to a canonical Git common directory (or canonical directory for non-Git inspection); workspace identity adds the canonical working directory. Branch/revision and supporting hashes constrain eligibility. Relocation does not silently merge unrelated repositories; an explicit future import operation must resolve identity.

Schema migrations are versioned, transactional where SQLite permits, and preceded by a recoverable backup. Newer unknown schema versions open read-only with an actionable error. Session events carry their own version; reducers reject unsupported events rather than skipping them.

## Configuration and model boundary

Product precedence: defaults, user configuration, explicit repository configuration, then user-confirmed TUI overrides. Credentials come exclusively from environment, never these files. Repository configuration cannot widen security capabilities; trusted user configuration owns permission grants.

Evaluation loads a committed nonsecret profile, then runtime AI_API_KEY. Model identity, endpoint, protocol, memory policy, tool policy, and budgets are locked for the task. Repository settings cannot override them, and TUI configuration cannot override the locked evaluation profile. Official amendments require a new profile and a new task, not a silent switch mid-session.

ModelProfile fields: provider, endpoint, model_id, protocol, tool_protocol (native/structured_json), context_window, max_output_tokens, generation_settings, optional seed, capability_flags, budget_settings. Context/output limits must be known and validated before a live run. Do not guess them from a model name.

`ModelGateway.generate(request) -> AsyncIterator[ModelEvent]` receives system instructions, valid messages, tool schemas, output limit, and cancellation/deadline. Events are text_delta, tool_call, usage, completed, error. Preserve provider-native continuation fields within an epoch. Do not execute partial streamed calls.

For structured_json, accept exactly one JSON action object per response: action=tool with tool/arguments, or action=finish with summary/evidence_ids. Reject extra prose, unknown fields/actions, and malformed JSON; feed validation feedback through the bounded recovery loop. Never execute shell-looking text from a normal answer.

## Development defaults

These values are testable initial settings, not official limits or optimization claims. Official configuration takes precedence.

| Setting | Default |
| --- | --- |
| Task wall-clock deadline | 1,800 seconds from start, including waits and retries |
| Model request budget | 100 physical requests across primary, workers, compaction, extraction, and retries |
| Verification/reporting reserve | Last 20% of request budget; no new discretionary exploration/delegation after reserve begins |
| Token budget | Explicit profile value if supplied; otherwise measured but uncapped, with request/time caps still enforced |
| Transient request retries | At most 2 additional attempts; delays 1s then 2s; honor a longer Retry-After only inside remaining deadline |
| Command timeout | 120 seconds; explicit extension up to remaining task time |
| Maximum concurrent workers | 2; delegation disabled by default until evaluation gate passes |
| Worker allocation | At most 10 requests per child; primary allocates from, never beyond, remaining shared budget |
| Repeated-failure threshold | 3 equivalent non-progressing settlements trigger strategy revision; 2 such interventions per task |
| Tool preview | At most 8,000 Unicode characters and 200 lines; include head/tail and artifact ID |
| Process output artifact | At most 16 MiB per process; drain and count discarded bytes after cap; flag lossy |
| Session artifact quota | 256 MiB; refuse new artifact-heavy work when full, preserve existing evidence |
| Storage retention | No automatic deletion of task evidence in v1; explicit cleanup never deletes durable records |
| Context headroom | Reserve configured max_output_tokens plus 10% of context_window; input budget is the remainder |
| Retrieved knowledge allocation | At most 10% of available input budget; pinned instructions/requirements take priority |
| Optional memory retrieval deadline | 200 ms locally; timeout falls back to direct inspection |
| Compaction overflow recovery | At most one repair attempt for the same logical model turn before any tool side effect |
| Process termination grace | 3 seconds after TERM, then KILL process group if still alive |

When reserves are exhausted, deterministic cleanup and artifact reporting remain possible; do not call the model beyond a hard cap. No seed or low temperature promises bitwise deterministic inference.

## Contract validation

All implementations validate record shapes, referential integrity, scopes, enum transitions, and effective profile digest. Test fixtures live under the future tests/ tree and are referenced by [evaluation](evaluation.md). Subsystem documents may refine behavior but must not redefine these contracts.
