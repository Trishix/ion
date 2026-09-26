# Ion Hackathon Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for native execution, or superpowers:subagent-driven-development if selected. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** deliver a TUI coding agent that uses configurable OpenAI-compatible provider profiles, makes guarded repository changes, and reports independently observable verification evidence.

**Architecture:** a single writer engine consumes normalized provider events, dispatches typed tools, and owns final outcomes. A minimal Textual client is built with the foundation and connected to the engine as it becomes available. The initial process is foreground; later durable sessions replace its host without replacing its contracts.

**Tech Stack:** Python 3.12, asyncio, Textual, HTTPX for async HTTP transport, Pydantic for validated records, JSON Schema validation for tool arguments, uv, pytest and pytest-asyncio. Resolve exact compatible versions and commit uv.lock during Task 1; do not invent version pins in this plan.

**Spec:** [approved core design](../specs/2026-09-26-hackathon-provider-and-core-design.md). Canonical records/defaults: [interfaces-and-data](../../interfaces-and-data.md). Long-term acceptance: [evaluation](../../evaluation.md).

## Global Constraints

- Locked evaluation credential input is exclusively `AI_API_KEY`; product mode accepts the profile's environment variable with `AI_API_KEY` as fallback. No credential values belong in configuration, logs, subprocess environments, or artifacts.
- The default development profile uses Groq Qwen. OpenRouter free Qwen and DeepSeek profiles and direct API profiles are selectable in product mode; live availability depends on the provider.
- `make setup`, `make run`, `make test`, and `make clean` are root targets. Setup and offline tests require no key.
- The TUI is the sole task interface. A scripted provider is an internal test fixture, not a second user-facing interface.
- Product mode permits model selection for the next task; evaluation mode locks model, endpoint, protocol, settings, and budgets.
- Do not ship an invented official model/profile. Official configuration and OPEN-01–07 remain release gates.
- One writer; exact patch preconditions; preserve the Git index and user changes. No automatic Git initialization, staging, reset, stash, commit, or publishing in Ion's runtime.
- Use canonical records from src/ion/contracts.py. Configuration aliases `base_url` and `model` normalize to ModelProfile.endpoint and ModelProfile.model_id.
- Development defaults: 1,800-second task deadline; 100 physical model requests; last 20% reserved; at most two transient retries after delays of 1 and 2 seconds; command timeout 120 seconds; TERM grace 3 seconds.
- Preview limits: 8,000 Unicode characters and 200 lines; process artifact cap 16 MiB; session quota 256 MiB. Output beyond a cap is drained and marked lossy.
- Context reserves configured max output plus 10% of the context window. Never silently trim original requirements or applicable instructions.
- This milestone is a demonstration core. Full P0 completion still requires durability, memory/context, and the official-environment gates in the existing specification.

## Review Focus

1. A newly selected provider endpoint could receive an existing credential unintentionally: trusted application profiles own endpoints; target-repository settings cannot replace them (Tasks 1–2).
2. Catalog discovery may omit capabilities or return models without known limits: no assumed context window and no eligibility based only on a model name (Task 3).
3. A streamed tool call may end midway through its arguments: no tool effects until a completed response validates (Task 2).
4. A user may edit the same file while Ion works: stale patches fail; overlapping changes prevent an Ion-attributed verified result (Tasks 4 and 6).
5. A process may emit a secret across output chunks or leave descendants: streaming redaction and actual descendant termination are required (Task 5).

## Phase Map

| Phase | Tasks | Exit evidence |
| --- | --- | --- |
| A — Runnable foundation | 1 | Locked installation, TUI shell, TOML validation, keyless tests |
| B — Live provider path | 2–3 | Normalized calls, catalog, capability gating, development model selection |
| C — Coding agent | 4–6 | Guarded edit and real check in a disposable repository; honest result |
| D — Demo delivery | 7–8 | Full TUI flow, doctor, offline acceptance report, reproducible setup |

Tasks are sequential because their interfaces depend on previous tasks. Native execution is recommended. Each task ends with its targeted checks; the final task runs the integrated suite and clean-environment workflow. Keep progress and deviations in the execution ledger.

## Task 1: Runnable foundation and validated profiles

**Files:** create Makefile, pyproject.toml, uv.lock, .python-version, .env.example, ion.toml, scripts/bootstrap.sh, scripts/clean.py, src/ion/{__init__,contracts,config,launcher}.py, src/ion/tui/{__init__,app}.py, tests/{test_config,test_packaging}.py; modify .gitignore and README.md.

**Interfaces:** `load_config(path: Path) -> AppConfig`; `resolve_profile(config: AppConfig, name: str, mode: Literal['product','evaluation']) -> ModelProfile`; `validate_task(input: dict) -> TaskSpec`; `IonApp(config: AppConfig)`; `main() -> int`. Define canonical enums and the TaskSpec, ModelProfile, ToolCall, ToolResult, ArtifactRef, VerificationEvidence, VerificationRecord and TaskResult shapes in contracts.py. Additional internal models include ModelRequest, ModelEvent, ModelInfo, ProbeResult and EngineEvent, with explicit discriminated event kinds.

- [ ] Write behavior tests: reject unknown config keys and literal credential fields; reject non-HTTPS live endpoints and embedded URL credentials; require environment variable names for keys; reject an evaluation profile that is not locked; preserve original task text. ModelProfile is immutable after resolution. Assert the default Groq Qwen profile resolves. Keep missing official profile as a structured error.
- [ ] Create the minimal package/test configuration needed to collect these tests; run `uv run pytest tests/test_config.py tests/test_packaging.py -q` and observe failures for missing behavior. Resolve dependencies with uv rather than hand-writing the lockfile. Fetch current documentation via Context7 before library-specific implementation.
- [ ] Implement the contracts, TOML parser using tomllib, and a TUI shell showing repository/task fields and provider status. Disable Run with an explicit engine-unavailable message until Task 6. Non-TTY launch fails with a terminal instruction; missing key does not prevent the shell from opening. Resolve committed configuration relative to the installed Ion project, never by silently loading the selected target repository's ion.toml.
- [ ] Pin uv and Python after inspecting supported local/CI platforms. Bootstrap into project-owned tooling directories with verified archive checksums; setup uses locked dependency sync. `make test` uses the installed environment without resolving or accessing the network. Clean only explicit disposable project paths and refuses symlink targets. `.env.example` contains only `AI_API_KEY=`.
- [ ] Run the targeted command; expected all pass. Run setup twice without a key; expected unchanged tracked sources and lockfile. Test clean with sentinel files and a symlink to an outside directory in a temporary project.
- [ ] Commit only this task's files: `feat: add runnable foundation and TOML profiles`.

## Task 2: Normalized provider gateway

**Files:** create src/ion/gateway.py, src/ion/providers/{__init__,openai_compatible,scripted}.py, src/ion/protocols.py, tests/{test_gateway,test_protocols}.py.

**Interfaces:** `ModelGateway.generate(request: ModelRequest) -> AsyncIterator[ModelEvent]`; `OpenAICompatibleProvider(profile: ModelProfile, credential: str, transport: AsyncBaseTransport | None = None)`; `ScriptedProvider(turns: Sequence[Sequence[ModelEvent]])`; `parse_action(text: str) -> ToolAction | FinishAction`. ModelRequest contains normalized history, tools, output cap, deadline and immutable profile digest. Event variants are text_delta, tool_call, usage, completed and error. Provider continuation fields remain private to the adapter and its history codec.

- [ ] Write tests using HTTPX mock transport: text response; complete native calls; split streamed JSON; truncated response; malformed arguments; auth/429/5xx errors; unknown token usage; cancellation. Assert no tool_call is emitted from an unfinished response, and native and structured calls normalize to equal tool/arguments values. Reject extra prose, duplicate JSON keys, extra fields and media content.
- [ ] Run `uv run pytest tests/test_gateway.py tests/test_protocols.py -q`; expected missing gateway/protocol behavior fails.
- [ ] Implement asynchronous chat-completions transport and normalized event/history codec. Buffer executable calls until completion; preserve native tool-call IDs and paired results. Disable implicit transport retries so the engine accounts for every physical attempt. Read the key only at the gateway boundary, disable cross-origin redirects and TLS bypass, and return sanitized errors. ScriptedProvider uses the identical event interface and never calls a network transport.
- [ ] Run the targeted command; expected all pass, including a fixture whose mock HTTP error contains a sentinel credential that must not appear in the result.
- [ ] Commit: `feat: normalize live and scripted model responses`.

## Task 3: Catalog discovery and capability checks

**Files:** create src/ion/models/{__init__,catalog,capabilities}.py, src/ion/model_selection.py, tests/{test_model_catalog,test_model_selection}.py; extend ion.toml and config.py.

**Interfaces:** `ModelCatalog.list(profile: ModelProfile, refresh: bool = False) -> CatalogResult`; `CapabilityProbe.run(profile: ModelProfile, gateway: ModelGateway) -> ProbeResult`; `select_model(profile: ModelProfile, model: ModelInfo, mode: str) -> ModelProfile`. CatalogResult includes entries and diagnostic status; ProbeResult contains text/tool support, protocol and profile digest. Limits are explicit metadata/configuration values, never inferred from a successful tiny probe.

- [ ] Test 300-second cache expiry with a fake clock; missing capability metadata; non-text entries; HTTP failure; malformed and empty catalogs; a 404 model-list endpoint with a manually configured model. Assert failed discovery leaves the active model unchanged. Assert evaluation selection is rejected and product selection returns a new profile without mutating the active task.
- [ ] Run `uv run pytest tests/test_model_catalog.py tests/test_model_selection.py -q`; expected failures.
- [ ] Implement GET /models discovery and a local vetted metadata map with source/date for limits. Verify Groq model limits against current official documentation before committing values. Permit user-configured compatible models only when required limits are explicit. Unknown models may appear as unavailable with the missing metadata explained; do not silently drop every model when provider metadata is sparse.
- [ ] Implement the read-only echo-tool probe; execute no repository command or patch. Native failure only permits a new structured_json profile when configuration allows it; no silent protocol mutation of a locked task. Cache by endpoint/model/protocol/settings digest for 300 seconds. Count live probes in diagnostics usage, and charge probes performed during a task to its physical-request budget. Do not run probes automatically during offline tests or TUI launch.
- [ ] Run targeted checks; expected catalog failure, stale probe, protocol lock and unknown-limit fixtures all pass.
- [ ] Commit: `feat: add model discovery and profile capability gating`.

## Task 4: Repository inspection and guarded patches

**Files:** create src/ion/tools/{__init__,registry,files,patches}.py, src/ion/{workspace,artifacts,instructions}.py, tests/{test_files,test_patches,test_instructions}.py.

**Interfaces:** `Workspace.capture(root: Path) -> WorkspaceBaseline`; `Workspace.fingerprint() -> str`; `Workspace.changes() -> ChangeSet`; `ArtifactStore.put(data: bytes, kind: str) -> ArtifactRef`; `InstructionResolver.resolve(repo: Path, paths: Sequence[Path]) -> list[InstructionSource]`; `ToolDispatcher.execute(call: ToolCall) -> ToolResult`. ChangeSet distinguishes attributable Ion edits, external files and ambiguous overlaps. Tool registry names/arguments follow execution-and-tools.md.

- [ ] Write real-filesystem tests for dirty staged/worktree files, exact text replacement, new/deleted files, traversal, symlink escape, binary input, stale hashes and multi-file prevalidation. Assert an invalid second hunk leaves every file unchanged. Assert unrelated external changes are absent from the Ion patch and same-file external edits mark attribution ambiguous. Cover AGENTS precedence and nested paths.
- [ ] Run `uv run pytest tests/test_files.py tests/test_patches.py tests/test_instructions.py -q`; expected failures.
- [ ] Implement bounded repo_list, literal/regex repo_search, file_read, patch_apply, diff_inspect, artifact_read and artifact_search. Give exact unified diff patches strict parsing and no fuzzy fallback. Capture original bytes and hashes, prevalidate all edits, stage temporary siblings and retain a manifest before renames. Full crash reconciliation remains a later milestone; unexplained manifests block further writes. Reject unsupported rename/mode/symlink edit operations explicitly.
- [ ] Store redacted output outside the target workspace, with hashes and completeness metadata. Scan relevant tracked/untracked files for fingerprints; record exclusions. Preserve the Git index. Load only root-to-target ancestor instructions; AGENTS.md wins over CLAUDE.md at the same directory. Resolve instructions again before touching a new subtree.
- [ ] Run targeted tests; expected pass with unchanged pre-existing staged content and intact outside-directory sentinels.
- [ ] Commit: `feat: add guarded repository tools and source evidence`.

## Task 5: Bounded repository commands

**Files:** create src/ion/{processes,redaction}.py, src/ion/tools/commands.py, tests/{test_processes,test_redaction}.py.

**Interfaces:** `CommandSupervisor.start(command: str, cwd: Path, timeout_seconds: float) -> ProcessHandle`; `poll(process_id: str, output_cursor: int) -> ProcessUpdate`; `cancel(process_id: str) -> ToolResult`; `close() -> None`. ProcessUpdate contains retained output cursor, state, exit code, discarded byte count and output artifact ID. Tool dispatcher maps command_start/poll/cancel to these methods; reject background=true in the demonstration core with a supported-feature error.

- [ ] Write real-process tests: bounded Unicode and huge-line output; closed stdin; cwd escape; nonzero exit; timeout; cancellation of a spawned descendant; unknown handles; quota exhaustion. Assert AI_API_KEY and known provider credentials are absent from child environments. Emit a sentinel secret in two chunks and assert it is absent from both previews and retained artifacts.
- [ ] Run `uv run pytest tests/test_processes.py tests/test_redaction.py -q`; expected failures.
- [ ] Implement separate process groups, sanitized allowlisted environment, continuous stdout/stderr draining, output quotas, redaction before persistence and bounded cursor reads. TERM then KILL after 3 seconds. Capture workspace deltas after commands and mark uncertain attribution conservatively. Serialize commands, verification and patches. App exit/cancellation terminates owned groups and preserves partial artifacts; no claim of crash-safe detached execution.
- [ ] Run targeted tests; expected actual descendants terminated and output consumers never deadlock after caps. Verify preview limits by Unicode character count as well as lines.
- [ ] Commit: `feat: supervise commands and redact retained output`.

## Task 6: Engine, request budgets and completion evidence

**Files:** create src/ion/{engine,budget,context,verification,progress}.py, tests/{test_agent_loop,test_budgets,test_verification}.py, tests/fixtures/bug_repo/; connect minimal app.py Run action.

**Interfaces:** `Engine.run(task: TaskSpec) -> TaskResult`; `Engine.events() -> AsyncIterator[EngineEvent]`; `Engine.cancel() -> None`; `BudgetLedger.admit(phase: Phase) -> RequestReservation`; `ContextManager.build(state: TaskState, profile: ModelProfile, phase: Phase) -> ContextPacket`; `CompletionGate.decide(state: TaskState, records: Sequence[VerificationRecord], changes: ChangeSet) -> Outcome`. Engine construction receives gateway, dispatcher, workspace and artifact store by dependency injection. No TUI logic belongs in the engine.

- [ ] Write an end-to-end scripted turn sequence that reads a buggy file, applies a guarded fix, runs its regression check and requests finish. Assert expected file bytes, evidence artifacts and verified outcome. Negative fixtures must reject invented evidence, zero collected tests, an unrelated successful command, a known failing check, post-test edits, missing artifacts and ambiguous patch ownership. Static-only evidence cannot verify a code-change task when executable checks are available.
- [ ] Add budget fixtures covering 100 physical attempts including retries, reserve admission at request 80, elapsed waits, cancellation and no credential in model-visible tool results. Run `uv run pytest tests/test_agent_loop.py tests/test_budgets.py tests/test_verification.py -q`; expected failures.
- [ ] Implement phases, native tool-result pairing and structured protocol feedback. `task_update` controls plan/hypotheses only; `finish_request` invokes the controller. Pin task/instructions and estimate the complete request; if necessary discard optional excerpts/history in complete interaction groups. Without compaction yet, a required packet that cannot fit returns a blocker. Apply three equivalent failures before strategy revision and at most two interventions.
- [ ] Build verification from settled operation records and independently parsed check output. Initial observers support pytest collected/pass/fail totals and explicit behavior commands with harness-defined expected outputs. Criterion-to-check mappings must be declared before observing the result and validated against changed paths/check scope. Unknown frameworks, generic exit-zero commands, or uncertain relevance yield unverified. Retain original criteria and never accept model assertions as coverage proof.
- [ ] Cleanup commands before final fingerprint calculation; invalidate checks on subsequent source/config changes. Render TaskResult from recorded evidence, final candidate diff and attribution. Use unavailable/unsatisfied criteria accurately; deterministic budget-exhausted reporting needs no final model request.
- [ ] Run targeted checks; expected end-to-end fixture passes and every false-success fixture remains non-verified. Run the minimal TUI against ScriptedProvider with a temporary repository.
- [ ] Commit: `feat: connect coding loop with budgets and verification gate`.

## Task 7: Model picker, doctor and complete task UI

**Files:** create src/ion/tui/{models,doctor,task,results}.py, src/ion/doctor.py, tests/{test_tui,test_doctor}.py; extend tui/app.py and launcher.py.

**Interfaces:** `Doctor.run(config: AppConfig, online: bool = False) -> list[DiagnosticCheck]`; each check is passed/failed/skipped with sanitized details. TUI receives the engine factory, catalog and doctor dependencies. It consumes EngineEvent and TaskResult without assigning task outcomes.

- [ ] Use Textual Pilot tests for repository confirmation, multiline task entry, Run, Cancel, slash-command routing, model picker, locked evaluation model, doctor and result inspection. Cover sizes 80x24 and 120x40. Assert offline doctor performs no network/model calls and missing credentials do not prevent navigation.
- [ ] Run `uv run pytest tests/test_tui.py tests/test_doctor.py -q`; expected missing flow failures.
- [ ] Implement `/models` as a modal catalog with current/available/unavailable states and visible missing capabilities. Selection affects only the next task. Implement `/doctor` with offline checks by default and an explicit live-check action showing that a probe consumes API requests. Display budgets, activity, candidate diff, commands and limitations. Run engine/network work asynchronously so navigation and Cancel remain responsive.
- [ ] Explain the initial foreground lifecycle in the TUI/README: exiting stops current work after cleanup; durable reconnect arrives in the next milestone. Support ION_REPO as the initial path hint and confirm the actual target before mutation.
- [ ] Run targeted tests and one manual interactive terminal smoke; expected task, model and evidence views work at both sizes with credential-safe error states.
- [ ] Commit: `feat: complete hackathon TUI and provider diagnostics`.

## Task 8: Reproducible demo and acceptance report

**Files:** create tests/e2e/test_demo.py, tests/test_clean.py, docs/releases/hackathon-core.md; update README.md, docs/README.md and docs/implementation-plan.md to link this plan and distinguish implemented/verified/deferred behavior.

**Interfaces:** internal fixture `run_demo(repo: Path, provider: ScriptedProvider) -> TaskResult` drives the same engine the TUI uses. It is not an end-user headless mode. Release report records revision, platform, dependency/profile digests, commands, outcomes and limitations.

- [ ] Add integration assertions that TUI submission produces the expected patch and fresh evidence and retains user sentinels. Add clean-target preservation and non-TTY launch checks. Run `uv run pytest tests/e2e tests/test_clean.py -q`; inspect any new failing behavior before fixing it.
- [ ] Finish evaluator instructions: externally export AI_API_KEY, make setup, make run, enter repository/task; make test is offline. Document trusted-local command execution, model transmission, unencrypted artifact retention, and current lifecycle limitations.
- [ ] Run `make test` with no API key and network access disabled after setup. Expected all current offline cases pass. In a fresh temporary checkout run setup twice, offline tests, and interactive launch. Retain output and verify source/lockfile stability and safe cleanup.
- [ ] If explicit live-test authorization and a credential are available, run the selected Groq model's read-only probe followed by a disposable bug fixture. Otherwise record live behavior as untested. Never substitute a scripted test for a live-provider result.
- [ ] Record EVAL coverage at scenario granularity. Mark durability, compaction, memory, workers and unresolved official requirements as pending. A demonstration milestone is not full P0 or submission readiness.
- [ ] Commit: `docs: record hackathon core acceptance and launch procedure`. Request the execution workflow's final independent review before any merge or release handoff.

## Subsequent Phases and Submission Gate

| Priority | Work | Existing task reference | Completion gate |
| --- | --- | --- | --- |
| Next | Durable sessions, ownership registry, process start gates, reconnect and recovery | implementation-plan Task 3 | EVAL-07 including orphan writer from another session |
| Next | Complete verification, attribution and budget recovery | Task 4 | All EVAL-10/11 core cases; no known false-success fixture |
| Next | Repository memory and full instruction lifecycle | Task 5 | EVAL-09 plus scope and forgetting checks |
| Next | Bounded context and atomic compaction | Task 6 | EVAL-08, including steering during compaction |
| Next | Session/evidence/memory TUI inspection | Task 7 | Remaining EVAL-02/13 interaction cases |
| Conditional | Read-only workers | Task 8 | Held-out benefit; remains off otherwise |
| Submission | Official adapter/profile, actual runtime, independent grading and freeze | Task 9 | All P0 scenarios and OPEN-01–07 resolved |

Official environment/profile integration moves earlier as soon as committee information arrives; it must not wait for optional workers. Offline benchmark fixtures and regression observations accumulate throughout implementation. The last phase validates the submitted revision and cannot be completed from documentation alone.

## Plan Self-review

The eight success criteria in the core spec map to Tasks 1/8 (setup), 1/7 (launch), 6/7 (task flow), 4/5/6 (tools and verification), 2/8 (offline suite), 2/3 (Groq and model selection), and 1/3/8 (evaluation lock and official profile gate). All five Review Focus failure modes have named owning tests. Shared signatures are defined once above and consumed by later tasks. The full v1 specification remains the authority for final competition readiness.
