# Hackathon Provider and Core Design

**Status:** approved design for the first implementation subproject  
**Date:** 2026-09-26  
**Scope:** the smallest complete Ion coding loop needed for a credible hackathon demonstration

## Intent

The first implementation milestone must let an evaluator launch Ion through the required Makefile workflow, enter a text task and repository in the TUI, let one text model inspect and change that repository through controlled tools, and receive a result backed by a relevant verification command.

This milestone optimizes for a working vertical slice. Durable detached sessions, crash reconciliation, reusable memory, compaction, and workers remain later subprojects. Their future interfaces must not force the hackathon core to be rewritten.

## Success criteria

The milestone is complete when all of the following hold:

1. `make setup` installs the locked project dependencies from a clean checkout without requiring an API key.
2. `make run` launches the Textual TUI. Locked evaluation reads the credential only from `AI_API_KEY`; product profiles may use their declared provider key with `AI_API_KEY` as fallback.
3. The TUI accepts a repository path and text task, displays the active profile and model, and starts one coding task.
4. The model can list and search repository files, read text, apply an exact preconditioned patch, run a bounded command, inspect the resulting diff, and request finalization.
5. Ion reports `verified` only when a relevant successful command is tied to the final workspace fingerprint. Otherwise it reports an honest non-verified outcome and preserves the candidate patch.
6. `make test` runs offline with a scripted provider and no credential.
7. Development mode defaults to Groq Qwen, with explicit profiles for OpenRouter Qwen/DeepSeek and direct APIs; compatible text models can be selected or configured.
8. Evaluation mode locks the committee-prescribed provider and model, once the exact IDs and endpoint are confirmed, and prevents runtime substitution.

## Delivery boundary

The first subproject contains four implementation phases:

1. **Foundation:** packaging, canonical core records, TOML configuration, Makefile targets, and an offline scripted provider.
2. **Provider path:** a small provider-neutral gateway, Groq support through its OpenAI-compatible API, capability validation, and model discovery.
3. **Coding loop:** guarded repository tools, the single-agent state loop, budget limits, and minimal evidence-based finalization.
4. **TUI and submission path:** task entry, `/models`, activity/diff/result views, doctor checks, and clean-environment Makefile verification.

Each phase must leave a runnable, testable increment. The hackathon demonstration does not wait for memory, workers, or crash-safe detached sessions.

## Provider architecture

Ion owns a narrow `ModelGateway` contract. Provider adapters translate their wire format into the same stream of text, tool calls, usage, completion, and typed error events.

The first adapters are:

- `ScriptedProvider`, used by the complete offline test suite;
- `OpenAICompatibleProvider`, which implements the shared chat-completions transport;
- a Groq profile that configures the generic adapter with `https://api.groq.com/openai/v1`.

Groq is configuration over the generic adapter rather than a separate agent implementation. Provider-specific behavior is isolated behind declared capabilities. The engine, tool validation, budgets, and verification do not depend on Groq response objects.

OpenRouter, OpenCode Zen, and other compatible gateways can later use the same adapter after an explicit profile and capability check. They are not dependencies of the hackathon baseline.

## Configuration contract

The repository contains a nonsecret `ion.toml`. Credentials are never stored in TOML, source, the Makefile, documentation examples, events, or artifacts.

```toml
schema_version = 1
default_profile = "groq-qwen-dev"

[profiles.groq-qwen-dev]
provider = "groq"
base_url = "https://api.groq.com/openai/v1"
model = "qwen/qwen3.8-27b"
api_key_env = "GROQ_API_KEY"
protocol = "openai_chat"
tool_protocol = "native"
text_only = true
locked = false
context_window = 131072
max_output_tokens = 4096

[model_catalog]
allow_runtime_discovery = true
cache_ttl_seconds = 300
require_text = true
require_tools = true
```

Product profiles read their declared provider-specific environment variable, with `AI_API_KEY` as fallback. Locked evaluation reads only `AI_API_KEY`, regardless of the profile's product credential name. No credential value is committed.

No placeholder committee model or endpoint is committed as an official profile. When the committee announces them, the release change adds one complete locked profile and makes it the evaluation default. `make run` must then select that profile without asking the evaluator to edit configuration or choose a provider.

Configuration precedence is:

1. application defaults;
2. committed `ion.toml`;
3. user-selected profile in product mode;
4. locked evaluation profile in evaluation mode.

Repository content cannot change the provider, endpoint, model, credential source, modality, or tool permissions. A task snapshots the effective profile and may not switch it mid-run.

## Model discovery and `/models`

In product mode, `/models` requests the configured provider's live model catalog when supported. Ion intersects that response with the profile policy and its local capability information, then shows eligible text models. Selecting a model creates a new effective task profile; it does not alter a running task.

The catalog cache is advisory and expires after 300 seconds. A network or authorization failure leaves the configured model usable if its profile is otherwise valid and reports model discovery as unavailable. An empty or malformed catalog never clears the configured model silently.

Provider model listings are not trusted as proof of agent suitability. Before a newly selected model can run a coding task, Ion checks required declared fields and performs a small capability probe when no valid cached result exists. The probe establishes:

- a text chat response can complete;
- either native tool calls or the strict structured-action fallback works;
- tool arguments satisfy the advertised JSON schema;
- the configured context and output limits are known rather than guessed from the model name.

In evaluation mode, `/models` is view-only and shows the locked model. Model discovery cannot replace it. Any attempted user, repository, or provider fallback that changes the model is a policy error.

## Tool protocol

Native function calling is preferred when the profile and capability probe permit it. Every call is validated against Ion's tool schema before execution.

Models without reliable native calls may use `structured_json`. That protocol accepts exactly one JSON object per model response:

- `{"action":"tool","tool":"...","arguments":{...}}`, or
- `{"action":"finish","summary":"...","evidence_ids":[...]}`.

Extra prose, unknown fields, malformed JSON, partial streamed objects, and unknown tools execute nothing. Ion returns bounded validation feedback within the task retry budget.

## Minimal coding loop

The engine uses the phases `intake`, `inspect`, `plan`, `act`, `verify`, and `finalize`, while keeping the implementation small enough for the hackathon slice.

1. Intake validates the profile, credential presence, repository path, task text, and budgets.
2. Inspect captures the initial workspace fingerprint and applicable repository instructions.
3. The gateway receives a bounded context and the permitted tool schemas.
4. Repository reads are bounded. Patches require the exact hash of every file being changed.
5. Commands run with closed stdin, a timeout, bounded retained output, and an environment that excludes `AI_API_KEY`.
6. `finish_request` enters controller-owned verification rather than declaring success.
7. Verification runs or validates a relevant command against the final workspace fingerprint, inspects the diff, and produces the final result.

The initial loop may run in the TUI process. The provider and engine boundaries must permit moving execution into the later durable session service without changing the model or tool contracts.

## TUI behavior

`make run` always launches the TUI and returns an actionable error when no interactive terminal is available. The first screen shows the selected repository, active provider/model, credential status without displaying the key, and task input.

The hackathon views are:

- task entry and repository confirmation;
- current phase and concise model/tool activity;
- changed files and diff;
- verification evidence and final outcome;
- a command palette containing `/models` and `/doctor`.

`/doctor` checks configuration parsing, credential presence, endpoint reachability, selected-model availability, known context/output limits, and cached capability-probe status. It must redact credentials and remain useful offline by distinguishing skipped network checks from failures.

## Error handling

- Missing `AI_API_KEY`: block a live task with a concise setup instruction; TUI launch and offline inspection remain available.
- Authentication failure: report the provider error category without retaining request headers or the credential.
- Rate limit or transient server failure: use at most the profile's bounded retry schedule and count every physical request.
- Unsupported tool calling: offer the configured structured-action protocol only if allowed by the profile; otherwise block the task.
- Invalid model response: execute nothing, provide bounded corrective feedback, and stop after the repeated-failure threshold.
- Stale patch input: reject the patch and require a fresh read.
- Command timeout: terminate the process group, preserve bounded output, and continue or finalize according to remaining budget.
- Verification unavailable: preserve the patch and report `unverified`; do not relabel it `verified`.

There is no automatic cross-provider or cross-model fallback during evaluation. In product mode, changing providers or models requires an explicit user selection and starts a new task profile.

## Security and rule compliance

The design implements the supplied hackathon rules as follows:

- the root Makefile owns `setup`, `run`, `test`, and safe `clean` targets;
- the live credential enters only through `AI_API_KEY`;
- every configured evaluation model is text-only;
- the effective evaluation model is explicit and locked;
- normal setup and offline tests do not require a credential;
- provider credentials are removed from repository subprocess environments;
- no profile contains a fallback that could substitute another model during official evaluation.

The local execution backend still assumes a trusted repository. Provider abstraction and guarded patches do not create an operating-system sandbox.

## Verification strategy

Implementation follows behavior-first tests for each phase. The offline suite uses temporary repositories and a scripted provider to prove:

- configuration rejects embedded credentials, invalid URLs, unknown fields, and forbidden evaluation overrides;
- model discovery filters ineligible entries and handles empty, stale, unauthorized, and malformed responses;
- native and structured tool calls normalize into the same validated internal call;
- the scripted end-to-end task creates the expected guarded patch and relevant command evidence;
- irrelevant green commands, zero collected tests, post-check source changes, and invented evidence cannot produce `verified`;
- `make setup` is repeatable and `make test` needs no key;
- Textual interaction tests cover task entry, `/models`, `/doctor`, diff inspection, and final outcome at narrow and normal terminal sizes.

A live Groq smoke test is opt-in and never part of the offline `make test` target. It records the effective model and checks a read-only tool round trip before running a disposable repository fixture.

## Later subprojects

After the hackathon core works, implementation continues in this order:

1. durable session journal, background engine, reconnect, process supervision, and crash reconciliation;
2. full verification controller, budget ledger, and recovery interventions;
3. source-linked repository memory and instruction lifecycle;
4. bounded context assembly and atomic compaction;
5. richer TUI session, evidence, and memory inspection;
6. optional read-only workers, enabled only after measured benefit;
7. independent live evaluation and the final committee profile freeze.

Each later subsystem receives its own design and implementation plan. The provider, tool, and result contracts from this core remain their integration boundary.
