# Ion product requirements

Status: approved design direction; foreground core implemented, full P0 product pending. Last updated: 2026-09-26.

## Purpose and users

Ion is an autonomous coding-agent harness that turns a text software-engineering request into reviewable repository changes and a report supported by execution evidence. It surrounds the prescribed foundation model with repository tools, durable task state, context management, recovery, and verification.

The first audience is hackathon evaluators working on supplied repositories and issues. The continuing product audience is developers using a terminal to fix bugs, add features, understand code, and resume interrupted work on trusted local repositories.

The first release is a competition-ready local product. Competitive ambition is measured through independently checked task resolution and resource efficiency; no claim of being the best or production-grade is made before evidence exists.

## Primary workflows

1. Evaluator runs the standard Makefile workflow; the launched TUI lets them select the target repository, supply issue text, and receive changes plus verification evidence.
2. Developer starts the TUI in or against a repository, submits a task, follows tool activity and diffs, and can steer, pause, cancel, or resume the task.
3. Developer reopens a session in the TUI after a crash; Ion reconciles unfinished operations and continues from durable state without blindly repeating mutations.
4. Developer inspects remembered repository knowledge in the TUI, sees its sources, and can forget it without silently deleting source transcripts.

Example: “Login sessions expire too early.” Ion identifies the duration calculation, reproduces the defect where practical, makes a scoped change, executes relevant tests, reviews the final diff, and reports whether those checks cover the intended behavior. A passing unrelated test cannot satisfy the task.

## Requirements and acceptance ownership

| ID | Requirement | Priority | Primary specification | Acceptance |
| --- | --- | --- | --- | --- |
| PRD-01 | Meet the standard setup, launch, credential, model, and text-only rules. | P0 | rules | EVAL-01–04 |
| PRD-02 | Inspect an existing repository and load applicable project instructions without changing user files. | P0 | context-management | EVAL-05, EVAL-13 |
| PRD-03 | Read/search files, apply guarded patches, run commands, inspect diffs, and update task state through typed tools. | P0 | execution-and-tools | EVAL-05, EVAL-06 |
| PRD-04 | Persist task requirements, execution history, operation outcomes, and artifacts across interruption. | P0 | task-lifecycle-and-verification | EVAL-07 |
| PRD-05 | Maintain bounded context through retrieval, output shaping, and atomic compaction. | P0 | context-management | EVAL-08 |
| PRD-06 | Store source-linked knowledge with scopes, contradiction handling, invalidation, and forgetting. | P0 | memory-architecture | EVAL-09 |
| PRD-07 | Verify acceptance criteria against the final workspace and report limitations honestly. | P0 | task-lifecycle-and-verification | EVAL-10 |
| PRD-08 | Enforce aggregate resource budgets, cancellation, bounded retries, and no-progress recovery. | P0 | task-lifecycle-and-verification | EVAL-06, EVAL-11 |
| PRD-09 | Launch a responsive TUI through make run; provide task entry, session control, and inspection in the TUI. | P0 | interfaces-and-data | EVAL-02 |
| PRD-10 | Support bounded, isolated research/review delegation with a single writer. | P1 | execution-and-tools | EVAL-11 |
| PRD-11 | Keep secrets out of logs and repository command environments; document local trust limits. | P0 | security | EVAL-03, EVAL-13 |
| PRD-12 | Provide reproducible offline checks, independent live grading, and performance comparisons. | P0 | evaluation | EVAL-01, EVAL-14 |
| PRD-13 | Expose inspectable session evidence, memory sources, effective configuration, and final artifacts. | P0 | interfaces-and-data | EVAL-02, EVAL-09, EVAL-10 |
| PRD-14 | Preserve user changes and durable task artifacts during editing, recovery, and cleanup. | P0 | execution-and-tools | EVAL-05, EVAL-07, EVAL-12 |

P0 is required before competition readiness can be claimed. P1 is a planned v1 capability but defaults off until its benefit is demonstrated; losing it does not disable the coding loop.

## Product scope

V1 includes a Python engine, Textual TUI, provider adapter, local event/state storage, filesystem artifacts, guarded file tools, managed commands, task/verification controllers, local repository memory, and evaluation fixtures. The TUI is the only user-facing task interface; there is no headless task mode, stdin/JSONL task protocol, web UI, editor client, or HTTP client. It works on text codebases across languages through repository commands; language-specific execution depends on the target repository's provisioned toolchain.

Native tool calling is preferred. A strict structured-action protocol supports a prescribed text model lacking native tool calls. Both must pass the same tool validation and execution policy.

V1 does not include hosted multi-tenancy, billing, accounts, a web IDE, autonomous publishing, automatic PR creation, unrestricted plugin loading, multi-writer coding teams, or mandatory vector infrastructure. It does not assume access to private GitHub issues: issue text and an existing repository are sufficient.

Planned extensions are a container execution backend, optional symbol/LSP navigation inside the TUI, opt-in external tool adapters, and semantic retrieval. New user-facing web, editor, HTTP, or headless interfaces are out of product scope. Internal service/socket protocols are implementation details, not public interfaces. Extensions must preserve the core contracts and earn inclusion through measured need. Windows support is deferred until process control and transport have an explicit implementation.

## User experience

The TUI presents task input/history, a progress list, tool activity, changed files/diff, verification status, and consumed/remaining budgets. It labels awaiting input, paused, interrupted, unverified, and failed states accurately. A concise activity summary is sufficient; private chain-of-thought is not a product requirement.

User steering is recorded durably and applied at the next safe boundary. New instructions amend the task explicitly; they do not erase prior requirements without recording what changed. Cancellation stops active tools and children and preserves the current patch.

The TUI never waits indefinitely for an approval or interactive program. Allowed local operations proceed under the selected policy; actions requiring a decision are presented as a blocked result with a concrete reason and a clear recovery action.

## Success measures

Primary: independently verified task resolution rate under the same model and budget. Secondary: false-success rate, tokens and time per resolved task, p50/p95 latency, tool validation failures, recovery success, and memory/context overhead.

Compare a minimal single-agent baseline with each proposed improvement using a fixed task manifest and recorded configurations. All critical offline scenarios must pass. Reusable memory and workers are not enabled merely because they exist; held-out results must justify their overhead. Statistical reporting is specified in [evaluation](evaluation.md).

## Constraints and dependencies

Organizer obligations and unresolved release dependencies are owned by [rules](rules.md). Canonical enums, defaults, and contracts are owned by [interfaces-and-data](interfaces-and-data.md). The model and runtime are not yet officially specified. The initial local backend assumes trusted repositories; it cannot safely isolate hostile code from the user's machine.

## Definition of product completion

The coding engine is feature-complete when P0 requirements pass their acceptance scenarios and the actual official profile works in the official environment. Documentation completion, baseline implementation, and submission readiness are separate milestones. Each release report must identify which milestone has been reached.
