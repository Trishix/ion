# Ion implementation plan

> For agentic workers: execute these tasks in dependency order using the Superpowers executing-plans workflow, or subagent-driven-development when explicitly selected. Keep source changes scoped to the task and preserve the shared contracts.

**Goal:** implement a competition-ready local coding harness with durable execution, bounded context, source-linked memory, and evidence-based completion.

**Architecture:** a Python session engine owns state and coordinates a provider gateway, typed tools, knowledge/context services, and verification. A TUI is the sole user-facing client. One agent writes; optional workers inspect immutable snapshots.

**Tech stack:** Python 3.12 development target, asyncio, SQLite/FTS5, Textual, uv, and pytest. Pin exact compatible releases during Task 1; validate against the official runtime before submission.

**Spec:** [PRD](prd.md), [architecture](architecture.md), and canonical [interfaces-and-data](interfaces-and-data.md); subsystem specifications are linked from [README](README.md).

This is the full runtime build plan. The foreground core and initial offline suite are implemented; the remaining P0 tasks below are still open. Commands below are acceptance targets only where their corresponding files exist.

The approved first milestone is now detailed in the [hackathon core implementation plan](superpowers/plans/2026-09-26-hackathon-core.md), based on the [provider and core design](superpowers/specs/2026-09-26-hackathon-provider-and-core-design.md). Execute its four phases first; use the remaining tasks below for full v1 delivery. The foreground demonstration core does not yet satisfy the durable session, memory, or compaction requirements for competition readiness.

## Current implementation checkpoint

| Phase | Current state | Next acceptance work |
| --- | --- | --- |
| A — Foundation | Root Makefile, locked dependencies, typed records, TOML profiles, TUI shell, and offline tests implemented | Clean-checkout reproducibility and full configuration edge cases |
| B — Provider path | OpenAI-compatible gateway, Groq and OpenRouter profiles, direct provider examples, `/models`, and `/doctor` implemented | Live credential probes for each intended provider and exact official model profile |
| C — Coding loop | Guarded file edits, bounded commands, artifacts, request budget, and pytest evidence implemented | Broader task criteria and independent verification fixtures |
| D — Product hardening | Run history persisted in SQLite; foreground TUI launches and exposes `/history` | Crash-safe operation journal, reconnection/resume, context compaction, repository memory, and complete P0 acceptance |

These are implementation checkpoints, not claims that the full acceptance scenarios below have passed.

## Global constraints

- Obey HK-01 through HK-13 and distinguish official requirements from POL policies and OPEN blockers in rules.md.
- In locked evaluation mode, read credentials only from AI_API_KEY and use the prescribed text-only model for every generative call. Product mode accepts a configured provider-specific environment variable with AI_API_KEY as fallback.
- Preserve user changes; no automatic Git initialization, commit, stash, reset, push, or publish as a task side effect.
- Keep one workspace writer, one session state writer, and bounded read-only workers.
- Use the exact records, enums, TUI contracts, and defaults in interfaces-and-data.md.
- No required hosted memory service, embedding model, account, or container daemon in the baseline.
- Record verification against the final workspace; task completion never follows a model stop signal alone.

## Review focus

1. A command changes files and the engine dies before recording success: resume must not duplicate effects.
2. A user edits code while Ion works: preconditions and verification must preserve/detect those edits.
3. Compaction drops a constraint or carries invalid provider metadata: retain deterministic task state and valid epochs.
4. A green command runs zero/irrelevant tests: it must not satisfy acceptance criteria.
5. A worker or remembered instruction requests broader authority: enforce scope/model/budget outside the model.

## Execution method

For each task, write the listed failing behavior tests first, run them and inspect the failure, implement the minimum behavior, then run the task checks and the full currently available offline suite. Test real files/processes/database transactions; simulate only the model/network boundary where determinism is needed. Do not claim a future acceptance case has passed because its test name is documented.

All public records live in src/ion/contracts.py. Once created, import them rather than redefining near-duplicates in each subsystem. Schema changes require updating the canonical specification and all consumers in the same change.

Runtime decisions that conflict with these documents must be recorded in research-and-decisions.md with rationale and acceptance impact. Routine internal function choices that do not alter contracts remain implementation details.

## Task 1 — Packaging, contracts, and offline skeleton

Depends on: documentation. Produces: installable ion entrypoint, versioned records, validated configuration, root Makefile.

Files: Makefile, README.md, pyproject.toml, uv.lock, .python-version, .env.example, src/ion/contracts.py, src/ion/config.py, src/ion/launcher.py, tests/test_contracts.py, tests/test_packaging.py.

Interfaces: load_profile(name) -> ModelProfile; validate_task(input) -> TaskSpec; TUI form submission emits TaskSpec without executing a model. ModelProfile is the configuration record specified in interfaces-and-data.

- [ ] Add tests for enum validation, result/outcome invariants, TaskAmendment projection, tagged VerificationEvidence (including valid command-free static evidence), invalid task text, locked evaluation overrides, and blank environment templates. Run `uv run python -m pytest tests/test_contracts.py tests/test_packaging.py`; expected initial failures identify missing behavior.
- [ ] Implement package/configuration/contracts and Makefile setup/test/clean. Bootstrap pinned uv/Python into project-owned tooling paths with verified downloads; use a committed lockfile and an isolated environment. Do not upgrade global pip.
- [ ] Implement the launch contract with an explicit unavailable-engine error until Task 2; do not label the skeleton submission-ready.
- [ ] Run tests and a fresh-environment setup twice; expected success without source modifications or an API key. Verify cleanup preserves sentinel user/session files.

Gate: EVAL-01's packaging portion, EVAL-03 secret-template checks, and EVAL-12 pass. Full launch readiness is deferred to Task 2, explicitly recorded.

## Task 2 — Model gateway and minimal TUI coding loop

Depends on: Task 1. Produces: one end-to-end local issue-solving path.

Files: src/ion/gateway.py, src/ion/providers/openai_compatible.py, src/ion/engine.py, src/ion/tools/registry.py, src/ion/tools/files.py, src/ion/tools/commands.py, tests/test_gateway.py, tests/test_agent_loop.py.

Interfaces: ModelGateway.generate(request) -> AsyncIterator[ModelEvent]; ToolDispatcher.execute(call) -> ToolResult; Engine.run(task) -> TaskResult. The OpenAI-compatible adapter is a development adapter, not an assumption about the unannounced official provider.

- [ ] Test native tool normalization, strict structured_json actions, malformed arguments, missing/invalid key, no secret inheritance, and the absence of image/audio inputs. Run `uv run python -m pytest tests/test_gateway.py tests/test_agent_loop.py`; observe intended failures.
- [ ] Implement gateway and the initial repo_list/repo_search/file_read/patch_apply/command/diff/task/finish tools with exact preconditions and bounded outputs.
- [ ] Implement the minimal TUI loop against a scripted provider and a temporary bug fixture. A verified result requires an actual relevant passing command and matching final fingerprint even in this baseline.
- [ ] Run the tests and full offline suite. A simulated end-to-end fixture must create the expected patch and evidence; a live smoke test is opt-in with explicit credentials/profile.

Gate: EVAL-02 TUI path, EVAL-04, basic EVAL-05/06/10. make run launches the TUI. No placeholder official model is committed as if prescribed.

## Task 3 — Durable sessions, process supervision, and recovery

Depends on: Task 2. Produces: session engine process/socket, event journal, artifacts, managed background commands, inspect/resume/pause/cancel.

Files: src/ion/session.py, src/ion/storage.py, src/ion/artifacts.py, src/ion/processes.py, src/ion/recovery.py, tests/test_recovery.py, tests/test_processes.py, tests/test_session_events.py.

Interfaces: SessionService methods from interfaces-and-data; EventStore.append(event, projection_update) -> seq; ArtifactStore.put(data) -> ArtifactRef; ExecutionBackend.start/poll/cancel; reconcile(session_id) -> TaskState or structured blocker.

- [ ] Test crashes before/after intent, partial multi-file patches, command effects before settlement, PID reuse, process-group cleanup, session A crash followed by session B write admission, spawn gating, missing artifacts, duplicate request IDs, and reconnect replay without event gaps. Run the three named test modules; confirm failures.
- [ ] Implement durable intent/settlement, atomic state projections, artifact finalization, workspace ownership registry/admission, recovery manifests, and unknown outcomes. Process wrappers wait for a durably recorded start gate and monitor owner loss.
- [ ] Implement session lifecycle and private socket transport; client detach must not cancel execution. Enforce output quotas and background readiness probes.
- [ ] Run fault injection repeatedly at each boundary plus the full offline suite; inspect resulting files and processes, not just event counts.

Gate: EVAL-06/07 and durable portions of EVAL-02/11/12. Never re-execute an unresolved mutation automatically.

## Task 4 — Verification controller and budgeted recovery

Depends on: Task 3. Produces: canonical completion gate, final reports, aggregate budget ledger, loop recovery.

Files: src/ion/verification.py, src/ion/budget.py, src/ion/progress.py, tests/test_verification.py, tests/test_budgets.py, tests/test_loop_recovery.py.

Interfaces: VerificationController.evaluate(state) -> criterion updates plus VerificationRecord list; CompletionGate.decide(state) -> Outcome or continue; BudgetLedger.reserve(request) -> reservation or budget error.

- [ ] Test invented evidence, irrelevant/zero-test success, pre-existing failures, post-test edits, unavailable checks, no-op/static-inspection tasks, cleanup changing source, unrelated external edits, and same-file attribution ambiguity. Test concurrent request admission and repeated-call false positives. Run named modules; confirm intended failures.
- [ ] Implement tagged criterion evidence, fingerprints, baseline comparison, separate observed/attributable patches, deterministic finalization, physical-request accounting, verification reserve, and bounded strategy interventions.
- [ ] Run known failing/correct fixture patches through the independent test observer and compare self-reported outcomes.
- [ ] Run the full offline suite; expected no known false-success fixture passes.

Gate: EVAL-10/11 and PRD-07/08. Runtime tests prove the claims that Task 2 only covered in the minimal path.

## Task 5 — Repository memory and instruction handling

Depends on: Tasks 3–4. Produces: source-linked local knowledge and scoped instruction resolution.

Files: src/ion/memory/store.py, src/ion/memory/retrieval.py, src/ion/memory/lifecycle.py, src/ion/instructions.py, tests/test_memory.py, tests/test_instructions.py.

Interfaces: MemoryStore.observe/query/invalidate/forget/profile as specified; InstructionResolver.resolve(repo, paths) -> ordered source-linked instructions. task_update remains owned by the session controller.

- [ ] Test branch/source changes, contradictions, hypothesized facts, derived dependency invalidation, tombstones/re-ingestion, scope leakage, FTS availability, and AGENTS/CLAUDE precedence. Run named modules; confirm failures.
- [ ] Implement SQLite records/relations/FTS, deterministic observation ingestion, profile selection, optional budgeted extraction, and readable summary exports outside the target repo.
- [ ] Implement memory inspect/forget commands; test that forgetting knowledge does not silently delete source artifacts.
- [ ] Run the full offline suite with both empty and stale knowledge stores.

Gate: EVAL-09 and instruction portions of EVAL-05/13. Evaluation cases begin with isolated reusable memory.

## Task 6 — Context assembly and atomic compaction

Depends on: Task 5. Produces: ContextPacket construction, selection manifests, safe context epochs.

Files: src/ion/context.py, src/ion/compaction.py, tests/test_context.py, tests/test_compaction.py.

Interfaces: ContextManager.build(state, profile, phase) -> ContextPacket; Compactor.compact(session, through_seq) -> ContextCheckpoint or structured error. Checkpoint record shape is canonical.

- [ ] Test undersized windows, tool-call pairing, repeated summaries, interrupted completion, signed provider metadata, post-intake “do not change dependencies” surviving repeated compaction, steering during compaction, deduplication, retrieval timeout, and one bounded overflow repair. Run named modules; observe intended failures.
- [ ] Implement complete-request estimation, reserve accounting, evidence selection, deterministic pinned state, bounded compaction inputs, checkpoint commit, and provider epoch rebuilding.
- [ ] Replay a long fixture through multiple compactions and confirm retained constraints, progress, and final verification.
- [ ] Run the full offline suite; compare context tokens and successful continuation against the uncompressed fixture.

Gate: EVAL-08/09/13. Smaller prompts without preserved behavior do not pass.

## Task 7 — TUI product and diagnostics

Depends on: Tasks 3–6. Produces: TUI, session browser, evidence/knowledge inspection, doctor.

Files: src/ion/tui/app.py, src/ion/tui/views.py, src/ion/client.py, tests/test_tui.py.

Interfaces: Internal client wraps the private session socket contract; the TUI consumes snapshots/events and sends control requests. It has no separate agent loop and is not exposed as a user-facing CLI/API.

- [ ] Test interactive-terminal launch and actionable non-TTY failure, cancelled requests, disconnect/reconnect, event deduplication, narrow terminals, and inspection without provider calls. Run named modules; confirm failures.
- [ ] Implement task input, repository selection, progress/tools/diff/verification/budget views, pause/cancel/resume, and credential-safe diagnostics.
- [ ] Run automated TUI tests and a manual terminal smoke check; record the supported environment.
- [ ] Run the full offline suite.

Gate: EVAL-02 and PRD-09/13. No hidden setup command beyond make run.

## Task 8 — Bounded delegation

Depends on: Tasks 4–7. Produces: opt-in research/review workers and their evaluation comparison.

Files: src/ion/workers.py, src/ion/snapshots.py, tests/test_workers.py.

Interfaces: WorkerCoordinator.delegate(goal, snapshot_id, request_budget) -> child handle; child results contain cited findings and usage, never parent outcomes.

- [ ] Test writes/shell/recursive delegation denied, snapshot completeness/quota, stale findings, same-model enforcement, atomic budget allocation, child timeout, and cancellation. Run `uv run python -m pytest tests/test_workers.py`; confirm failures.
- [ ] Implement child transcripts, immutable eligible-source snapshots, scope filtering, read-only tools, and result validation.
- [ ] Run the full offline suite and paired held-out worker/no-worker experiments from evaluation.md.
- [ ] Keep default off unless the documented benefit gate passes; record the decision and costs.

Gate: EVAL-11 and PRD-10. A failed benefit gate does not block the single-agent product.

## Task 9 — Independent evaluation and submission freeze

Depends on: P0 tasks; Task 8 only if workers ship enabled. Produces: repeatable evaluation runner and release report.

Files: tests/e2e/, tests/fixtures/, evals/manifest.json, evals/runner.py, evals/grader.py, README.md, nonsecret official profile, release report under docs/.

Interfaces: evaluate_case(manifest_entry, profile) -> independent grade plus TaskResult/usage references; grader data is outside the agent's tool scope.

- [ ] Add fixture tests for manifest pinning, protected grading, unknown usage, failed-attempt accounting, and cold-memory resets; confirm failing behavior before runner implementation.
- [ ] Implement offline and live evaluation separation, per-case artifacts, paired comparison reports, and all EVAL-01–14 scenarios.
- [ ] Resolve OPEN-01–07 with actual organizer data; freeze dependency/runtime/profile revisions.
- [ ] Execute the full clean-environment Makefile workflow, secret scan, supported-platform suite, and live prescribed-model smoke/evaluation. Record exact evidence and remaining limitations.

Gate: all P0 acceptance scenarios pass; official environment launch works; no unresolved compliance blocker. Do not claim runtime completion from this document alone.

## Deferred work

Container isolation, Windows, public APIs, editor/HTTP/web clients, headless task interfaces, semantic retrieval, LSP, external tools, and hosted collaboration are out of current product scope. Any future reconsideration requires an explicit product decision and measured acceptance criteria; none may quietly become competition prerequisites.
