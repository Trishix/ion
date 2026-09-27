# Agile delivery guide

Ion is developed in small, reviewable slices. This document is the living delivery guide; it replaces long-lived implementation plans and design drafts.

## Working agreement

1. Start from a user-visible outcome or a failing check.
2. Keep each change narrow enough to review in one pull request.
3. Update the owning reference document when a behavior or contract changes.
4. Add or update a focused test with the implementation.
5. Run `make test` before merging. Record live-provider checks separately from offline verification.
6. Keep credentials, generated caches, and local run data out of Git.

## Current increments

| Increment | Shipped behavior | Primary reference |
| --- | --- | --- |
| Provider reliability | OpenAI-compatible profiles, live catalog checks, tool capability validation, retry/backoff handling, `/doctor`, and `/connect` | [Provider and model configuration](../README.md#choose-a-provider) |
| Coding loop | Repository inspection, guarded edits, bounded commands, tool settlement, steering, diff capture, and honest completion outcomes | [Execution and tools](execution-and-tools.md), [Task lifecycle](task-lifecycle-and-verification.md) |
| Durable operation | SQLite session journal, private session socket, workspace ownership claims, recovery gates, `/sessions`, `/inspect`, and `/resume` | [Architecture](architecture.md), [Task lifecycle](task-lifecycle-and-verification.md) |
| Context and memory | Instruction precedence, bounded context, compaction checkpoints, scoped source-linked memory, stale references, and loop detection | [Context management](context-management.md), [Memory architecture](memory-architecture.md) |
| Verification and operations | Criterion-aware checks, artifacts, diagnostics, redaction, process cleanup, read-only workers, and evaluation fixtures | [Evaluation](evaluation.md), [Security](security.md) |

## Next slice

Choose the smallest missing capability that improves autonomous coding reliability. Good candidates are an official evaluation profile once organizers publish it, more provider fixtures, detached client-independent execution, and additional recovery/evaluation scenarios. Do not create a new planning document for a slice; open an issue or PR with:

- the user outcome and acceptance criteria;
- the owning runtime and documentation files;
- the focused test or live check;
- known limitations and rollback notes.

## Definition of done

A slice is done when the code, focused tests, reference documentation, and user-facing error path agree. The full offline suite is green, the diff contains no generated or secret material, and any live-provider result includes the provider, model, date, and scope of the check.

## Release gate

The hackathon entry path remains `make setup`, `make run`, and `make test`. Organizer-specific model, runtime, network, budget, and submission details remain tracked as open questions in [rules](rules.md); until they are supplied, describe the project as a working local harness rather than an officially frozen submission.
