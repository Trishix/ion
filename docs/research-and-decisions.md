# Research comparison and architecture decisions

Status: decision record supporting the v1 specification. Research inspected 2026-09-26; repository links below are pinned, not moving-branch promises.

## Source register and authority

| Source | Identity | Role and limits |
| --- | --- | --- |
| Organizer guidelines and problem statement | User-supplied text in this conversation, 2026-09-26 | Normative hackathon requirements; no official URL, model, runtime, numerical score, or deadline supplied. Transcribed in [rules](rules.md). |
| Teammate PDF | ai_harness_hackathon_prd_final.pdf; six pages; titled “AI Development Harness: Standardized System Architecture”; dated September 26, 2026 | Alternative PRD/HLD/LLD proposal. All six pages' extractable text inspected. Not an organizer rules amendment. |
| PDF checksum | SHA-256: 02ad1234e9bfce6b356fe66f3cdcc3cb0de488aa1e2a14185bc669aef49d8287 | Identifies the reviewed local source without committing the PDF or depending on a machine-specific path. |
| OpenCode | b65de4d6943ef35337f8f2bfdbb369f6d25e7e9f; dev revision dated 2026-09-26 | Selected implementation files, event design, security model, and docs inspected; not an exhaustive audit. |
| Supermemory | cfa6c7cb17476d19ea896867406c80e8186a72ec; main revision dated 2026-09-25 | Concept docs and public integration code inspected. Internal learning engine algorithms are not established by those integrations. |
| LangGraph documentation | Official docs retrieved through Context7 during comparison | Evaluated checkpoint/store and replay semantics; not selected as a dependency. |

Context7 was used for current OpenCode, Supermemory, and LangGraph documentation. Source inspection checked concrete claims where possible. OpenCode's repository contains evolving implementations and specifications; do not conflate a v2 spec with every deployed release.

## PDF comparison

| PDF proposal | Pages | Disposition | Reason and destination |
| --- | --- | --- | --- |
| Text-only inputs/models and AI_API_KEY | 2–3 | Adopt | Matches organizer rules; rules.md and gateway contract. |
| Root Makefile and evaluation flow | 2–3, 6 | Adopt intent, revise packaging | Locked isolated setup, keyless offline tests, safe cleanup; avoid global pip upgrades and an unpinned sandbox image. |
| gpt-oss-120b / qwen3-32b and Groq/OpenAI-compatible gateway | 2–3 | Reject as official defaults | No committee model/provider announced. Adapter boundary remains; official profile is a release dependency. |
| Single-loop asynchronous state machine | 2, 4 | Adopt | Matches primary-agent design; durable task controller owns transitions. |
| LangGraph StateGraph | 2–5 | Considered, not selected | An explicit engine fits the chosen loop; framework checkpoints would still need side-effect reconciliation. |
| Per-task Docker, worktree isolation, network disabled | 2–3, 6 | Defer backend, retain separation | User chose trusted local v1. Worktrees are not sandboxes; dependency provisioning and network restrictions need separate treatment. |
| Credentials inside task container | 6 | Reject | Keep key in gateway, outside repository execution environment. |
| Pre/post diff and verification gate | 3–4 | Strengthen | Compare against captured dirty-workspace baseline; tie checks to final fingerprint and criteria. A “clean diff” cannot mean no intended changes. |
| SQLite telemetry/logs | 3 | Strengthen | Also own event journal, typed operation settlement, task projections, and knowledge index. |
| Typed AgentState | 5 | Strengthen | Split task state, operation/process records, provider history, evidence, and budgets; do not make an ever-growing messages list the entire state. |
| Short commands versus daemons | 4–5 | Adopt and harden | Process groups, persistent handles, readiness probes, bounded output, and cleanup; avoid relying on a daemon thread or stdout signature alone. |
| In-context, disk pointer memory, project rules | 5 | Adopt concepts, revise authority | Structured stores are authoritative; readable summaries are derived views; instructions are loaded separately. |
| CLAUDE.md instructions | 5 | Adapt | AGENTS.md first with explicit CLAUDE.md compatibility fallback and directory scope. |
| Isolated search subagents | 6 | Adopt | Bounded read-only snapshot contexts, cited findings, shared prescribed model and budget. |
| 8,000-character middle truncation | 6 | Adapt | Bounded head/tail/error previews plus retained artifacts and explicit loss indicators; cap lines and disk use too. |
| Noninteractive environment and yes piping | 6 | Adopt explicit options, reject blanket yes | Automatic agreement can authorize unintended behavior; closed stdin and interaction_required are predictable. |
| Fuzzy Levenshtein edit fallback | 6 | Reject for v1 | Similar code blocks create wrong-location risk; stale-input response and reread are auditable. |
| Three-turn loop warning | 6 | Adapt | Compare inputs, results, and workspace progress; exclude legitimate polling; bound strategy interventions. |
| Security statements marked cite placeholders | 6 | Do not treat as sourced rules | PDF citation placeholders do not identify an official security requirement. |

## OpenCode observations and adaptations

**OC-01 — durable events.** Its [sync design](https://github.com/anomalyco/opencode/blob/b65de4d6943ef35337f8f2bfdbb369f6d25e7e9f/packages/opencode/src/sync/README.md) describes single-writer sequencing and projection-based event persistence. Ion adopts one authoritative session writer and separates replayable events from live fragments; it does not reproduce OpenCode's compatibility layers.

**OC-02 — compaction.** The inspected [core compaction implementation](https://github.com/anomalyco/opencode/blob/b65de4d6943ef35337f8f2bfdbb369f6d25e7e9f/packages/core/src/session/compaction.ts) uses a structured rolling summary, recent context, complete-request estimation, and start/end events. Ion adds deterministic pinned TaskState and atomic checkpoint validation; source constants are not assumed optimal for the unknown official model.

**OC-03 — tool outputs.** The [truncation implementation](https://github.com/anomalyco/opencode/blob/b65de4d6943ef35337f8f2bfdbb369f6d25e7e9f/packages/opencode/src/tool/truncate.ts) bounds output and supplies a path to retained text. Ion uses opaque artifact references, explicit disk quotas, completeness flags, and protected evidence retention.

**OC-04 — children and loops.** The [task tool](https://github.com/anomalyco/opencode/blob/b65de4d6943ef35337f8f2bfdbb369f6d25e7e9f/packages/opencode/src/tool/task.ts) has child-session identity, permissions, and depth control. The [session processor](https://github.com/anomalyco/opencode/blob/b65de4d6943ef35337f8f2bfdbb369f6d25e7e9f/packages/opencode/src/session/processor.ts) includes repeated-call detection. Ion retains bounded delegation but permits only read-only children in v1 and adds shared-budget admission.

**OC-05 — instructions and tools.** The [instruction loader](https://github.com/anomalyco/opencode/blob/b65de4d6943ef35337f8f2bfdbb369f6d25e7e9f/packages/opencode/src/session/instruction.ts) and [registry](https://github.com/anomalyco/opencode/blob/b65de4d6943ef35337f8f2bfdbb369f6d25e7e9f/packages/opencode/src/tool/registry.ts) demonstrate explicit instruction discovery and tool registration. Ion specifies its own precedence and minimal tool surface; not all provider/plugin features belong in the competition baseline.

**OC-06 — permission limits.** Its [security policy](https://github.com/anomalyco/opencode/blob/b65de4d6943ef35337f8f2bfdbb369f6d25e7e9f/SECURITY.md) states that permission prompts are not sandbox isolation. Ion makes the same distinction explicit rather than advertising local permission checks as a security boundary against hostile code.

## Supermemory observations and adaptations

**SM-01 — sources and extracted facts.** The [graph-memory documentation](https://github.com/supermemoryai/supermemory/blob/cfa6c7cb17476d19ea896867406c80e8186a72ec/apps/docs/concepts/graph-memory.mdx) distinguishes documents from atomic memories and describes updates, extensions, derivations, and forgetting. Ion applies those concepts to code facts with file hashes, evidence categories, and conservative invalidation; inferred facts never become verification records.

**SM-02 — asynchronous learning.** The [pipeline documentation](https://github.com/supermemoryai/supermemory/blob/cfa6c7cb17476d19ea896867406c80e8186a72ec/apps/docs/concepts/how-it-works.mdx) separates indexed documents from subsequent memory extraction. Ion separates synchronous task/evidence persistence from optional asynchronous knowledge extraction. It does not require Supermemory's internal learning model.

**SM-03 — profiles and scope.** [Profiles](https://github.com/supermemoryai/supermemory/blob/cfa6c7cb17476d19ea896867406c80e8186a72ec/apps/docs/concepts/user-profiles.mdx) describe stable and dynamic context. [Container tags](https://github.com/supermemoryai/supermemory/blob/cfa6c7cb17476d19ea896867406c80e8186a72ec/apps/docs/concepts/container-tags.mdx) describe scoped organization/access. Ion adopts explicit session/repository/user scopes and a bounded profile; its own database must enforce them.

**SM-04 — replacement and deduplication.** The public [context wrapper](https://github.com/supermemoryai/supermemory/blob/cfa6c7cb17476d19ea896867406c80e8186a72ec/packages/tools/src/shared/memory-context.ts) replaces managed context and escapes delimiters. The [memory client](https://github.com/supermemoryai/supermemory/blob/cfa6c7cb17476d19ea896867406c80e8186a72ec/packages/tools/src/shared/memory-client.ts) handles profile/search deduplication. Ion adopts those integration goals without copying the provider-specific wire format or elevating retrieved text into trusted policy.

**SM-05 — explicit forgetting.** The [forget helper](https://github.com/supermemoryai/supermemory/blob/cfa6c7cb17476d19ea896867406c80e8186a72ec/packages/tools/src/shared/forget-memory.ts) exposes a memory lifecycle operation. Ion makes forgetting local, scoped, and distinct from deleting original artifacts.

No marketing latency, context-reduction, or benchmark number is adopted as an Ion target or measured result. Local lexical retrieval is the initial implementation; semantic/vector infrastructure needs its own evidence and official-model review.

## Decision register

| ID | Decision | Tradeoff / revisit trigger |
| --- | --- | --- |
| DEC-01 | Python local-first engine with TUI and headless clients | Faster single-runtime iteration; revisit transport/backend for supported new platforms. |
| DEC-02 | Own explicit state machine, not LangGraph dependency | More recovery implementation; revisit if orchestration complexity exceeds the tested core. |
| DEC-03 | Single workspace writer; bounded read-only workers | Less parallel editing; add writers only with isolated branches and proven merge/verification semantics. |
| DEC-04 | Durable session journal separate from reusable knowledge | Additional schema design; enables different authority and lifecycle rules. |
| DEC-05 | Model profile locked across every generative call | Limits provider-specific shortcuts; required for prescribed-model fidelity. |
| DEC-06 | Local execution default; container backend deferred | Requires trusted repositories; add isolation before supporting hostile code or hosting. |
| DEC-07 | Source-linked relational memory with FTS5 | Less semantic matching; add vectors only after a held-out evaluation benefit. |
| DEC-08 | Atomic compaction with pinned requirements and preserved evidence | Compaction has model cost; avoids summary-only recovery. |
| DEC-09 | Exact edit preconditions and explicit unknown outcomes | More rereads/reconciliation; prevents silent fuzzy writes and unsafe replay. |
| DEC-10 | Controller-owned verification and independent evaluation | Cannot guarantee untested correctness; improves honesty and measurable reliability. |
| DEC-11 | Public contracts before extra clients/plugins | Slower feature breadth; protects core invariants as product grows. |
| DEC-12 | Competition memory starts fresh across cases | Loses warm-start advantage; revisit only with explicit official allowance and separate reporting. |

The independent documentation review on 2026-09-26 refined four implementation contracts: workspace-wide recovery admission blocks new sessions around orphan commands; observed workspace deltas are separate from attributable Ion edits; authoritative TaskAmendment records preserve later constraints across compaction; and tagged VerificationEvidence represents executable, observation, and static checks without fabricated command links. These refinements strengthen DEC-03/08/09/10 and are covered by EVAL-05/07/08/10.

LangGraph's [persistence documentation](https://docs.langchain.com/oss/python/langgraph/persistence) distinguishes checkpointers and cross-thread stores; its [functional API guidance](https://docs.langchain.com/oss/python/langgraph/functional-api) explains replay and idempotent side-effect handling. These informed DEC-02/04; choosing a framework would not itself make arbitrary commands exactly-once.

## Research limits and maintenance

The PDF's diagrams were available through its extracted text; this comparison focuses on stated architecture/behavior, not typography. Remote sources were inspected selectively at the pinned revisions. An architecture document is not a reproduction of either project's complete implementation or a benchmark validation.

All prose and Ion contracts here are original synthesis; no dependency source is vendored. If implementation later copies source, inspect that component's license at its exact revision and preserve required attribution.

Revisit decisions through a dated change to this register with supporting evidence, affected requirements, and migration implications. New upstream commits do not automatically change Ion's contract.
