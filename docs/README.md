# Ion product documentation

Ion is a planned autonomous coding-agent harness for the AI Harness Hackathon 2026 and a continuing local developer product.

**Current status:** documentation only. The engine, TUI, Makefile, tests, and model integrations described here are not implemented. No benchmark score or submission-readiness claim is made.

## Read in this order

| Document | Owns |
| --- | --- |
| [Hackathon rules](rules.md) | Organizer obligations, team policies, compliance checks, and unresolved official details |
| [Product requirements](prd.md) | Users, workflows, requirements, scope, and success measures |
| [System architecture](architecture.md) | Components, process boundaries, storage ownership, and data flow |
| [Interfaces and data](interfaces-and-data.md) | TUI launch/interaction contract, internal methods, schemas, enums, defaults, and configuration |
| [Memory architecture](memory-architecture.md) | Knowledge sources, scopes, relationships, freshness, retrieval, and forgetting |
| [Context management](context-management.md) | Model-visible context, instruction precedence, token budgets, and compaction |
| [Execution and tools](execution-and-tools.md) | Tool contracts, guarded edits, process supervision, delegation, and backends |
| [Task lifecycle and verification](task-lifecycle-and-verification.md) | Task transitions, crash recovery, evidence, budgets, and outcome gate |
| [Security](security.md) | Trusted-local assumptions, capabilities, credentials, privacy, and isolation limits |
| [Evaluation](evaluation.md) | Offline scenarios, live benchmarks, ablations, and release procedure |
| [Implementation plan](implementation-plan.md) | Dependency-ordered runtime tasks, interfaces, and acceptance gates |
| [Research and decisions](research-and-decisions.md) | Teammate-plan comparison, pinned upstream evidence, alternatives, and rationale |

Start with rules/PRD/architecture; implementers must also read interfaces-and-data and the relevant subsystem document. Evaluation is the acceptance authority for tested behavior, not a set of claimed current results.

## Source and decision hierarchy

Organizer rules outrank implementation preferences. Explicit user decisions define product scope. The teammate PDF and public projects are design evidence, not additional hackathon rules.

The approved baseline is Python, competition core first, local trusted repositories, one primary writer, optional bounded read-only workers, a prescribed text model, and local memory without required extra service credentials.

Requirements use HK-* for organizer rules, POL-* for Ion policies, OPEN-* for official unknowns, PRD-* for product requirements, EVAL-* for validation scenarios, and DEC-* for architecture decisions. Links between them provide traceability.

## Document ownership

Shared states/types/defaults are defined once in interfaces-and-data. rules is the only owner of organizer strictness. Subsystem documents explain behavior and reference those definitions. implementation-plan describes future work; it does not override the specification.

Change a contract in its owner document first, update affected consumers/evaluation cases, and record significant tradeoffs in research-and-decisions. Keep proposed, implemented, and verified claims distinct.

## Glossary

| Term | Meaning |
| --- | --- |
| Session | Durable interaction/execution record with ordered events and a reconnectable TUI |
| Task | One user/organizer objective with criteria, scope, and budget |
| Workspace | A specific working directory; separate worktrees are separate workspaces |
| Repository identity | Knowledge namespace associated with the underlying repository, with revision/hash applicability |
| Operation | One validated tool action with durable intent and settlement |
| Artifact | Managed file containing retained output, source snapshot, patch, or other evidence |
| Memory | Reusable source-linked knowledge, distinct from authoritative execution records |
| Context | Bounded model-visible selection of instructions, state, evidence, and knowledge |
| Checkpoint | Committed compacted-context boundary anchored to durable task state and events |
| Verified | Required criteria have sufficient fresh evidence; not a guarantee of untested correctness |
| Snapshot | Immutable eligible-source/artifact view used for a worker or verification record |
| Profile | Either a locked execution/model configuration or a small memory summary; documents qualify which meaning is intended |

## Release blockers

The organizers have not supplied the exact model/API, runtime/OS, task transport, budgets/scoring, network policy, reusable-memory policy, or final submission details. OPEN-01–07 in rules tracks them. They do not block building the offline core, but must be resolved before calling the product submission-ready.

## Documentation verification

Documentation validation completed on 2026-09-26:

- 13-document inventory, Markdown table/fence structure, and 41 local links checked with no errors.
- 17 unique external source links returned successful HTTP responses.
- All five Mermaid diagrams parsed successfully with Mermaid 11.0.0.
- 68 requirement/policy/open-question/decision definitions checked for uniqueness and references; every PRD requirement maps to evaluation scenarios.
- Independent architecture review identified four gaps; workspace-wide orphan recovery, patch attribution, compaction-safe amendments, and tagged verification evidence were corrected and corresponding contract checks passed.
- A targeted credential-pattern scan found no matches; this is not a comprehensive future release secret audit.

Validation tooling ran from a temporary directory outside this project; no product dependencies, Git repository, or runtime code were created. Runtime scenario results remain pending implementation. Do not treat any future test command in implementation-plan as an executed test.
