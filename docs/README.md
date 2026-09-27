# Ion documentation

Ion is a local autonomous coding harness. The foreground TUI accepts a task, inspects a repository, applies guarded edits, runs bounded checks, records evidence, and reports an honest outcome.

## Start here

1. [Root README](../README.md) — install, launch, providers, commands, limits, and the current live smoke result.
2. [Agile delivery guide](agile.md) — how increments are planned, tested, documented, and released.
3. [System architecture](architecture.md) — runtime components, ownership, storage, and data flow.
4. [Execution and tools](execution-and-tools.md) — tool contracts, process supervision, edits, and workers.
5. [Task lifecycle and verification](task-lifecycle-and-verification.md) — recovery, evidence, budgets, and outcomes.

## Reference by concern

| Document | Use it for |
| --- | --- |
| [Rules](rules.md) | Organizer obligations and unresolved official details |
| [Interfaces and data](interfaces-and-data.md) | Shared records, states, defaults, and configuration |
| [Context management](context-management.md) | Instruction precedence, context budgets, retrieval, and compaction |
| [Memory architecture](memory-architecture.md) | Scoped source-linked memory, freshness, retrieval, and forgetting |
| [Evaluation](evaluation.md) | Offline suite, live checks, evidence, and release verification |
| [Security](security.md) | Trusted-local assumptions, capabilities, secrets, and isolation limits |

The runtime reference documents describe shipped behavior. The agile guide owns sequencing and future slices; avoid reviving a second long-lived plan or spec.

## Current implementation

- Python 3.12–3.13 package with a Textual TUI and `make` entrypoints.
- OpenAI-compatible provider gateway with configured profiles, live model catalog discovery, capability checks, retry handling, `/connect`, and `/doctor`.
- Economy and legacy execution modes with request/token admission, bounded retries, context compaction, and usage diagnostics.
- Guarded repository reads and writes, supervised commands, artifact storage, workspace ownership claims, and conservative recovery.
- SQLite-backed session/event records, private control socket, `/sessions`, `/inspect`, `/resume`, and in-flight steering.
- Scoped repository memory, stale-source invalidation, bounded workers, loop detection, redaction, and criterion-aware verification.

## Documentation hygiene

When behavior changes, update its owning reference document and the relevant command examples. Keep proposed organizer details in [rules](rules.md), and keep product work in issues or pull requests described by [agile.md](agile.md). Do not add historical planning documents to the runtime documentation set.
