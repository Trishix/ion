# Memory architecture

Status: normative v1 design. Owns reusable knowledge behavior; [interfaces-and-data](interfaces-and-data.md) owns record shapes and constants.

## Authority and memory categories

Memory is a set of durable observations and retrieval aids. It is not an unbounded transcript pasted into each prompt and is not a source of execution permissions.

| Category | Store | Authority and use |
| --- | --- | --- |
| Working task state | Session database | Current requirements, plan, hypotheses, failed approaches, next action; controller validates updates. |
| Episodic evidence | Session journal and artifacts | Recorded file observations, operations, patches, and verification; source for audit and recovery. |
| Repository knowledge | Repository knowledge database | Entry points, conventions, commands, relationships; reusable only when supporting sources remain applicable. |
| Learned procedures | Repository knowledge database | Prior successful/unsuccessful approaches with environment and evidence; advisory, never auto-executed. |
| User profile | Product-mode knowledge scope | Explicit preferences and stable context; never imported into isolated evaluation cases. |

Project instructions such as AGENTS.md are authoritative within their declared task scope subject to user and harness policy. They are loaded separately from learned facts. A generated MEMORY.md-style summary cannot replace those instructions or the event journal.

## Observation and extraction pipeline

```mermaid
flowchart LR
    Source["File, user statement, or tool result"] --> Evidence["Persist source evidence"]
    Evidence --> Candidate["Extract candidate fact"]
    Candidate --> Validate["Validate scope and source references"]
    Validate --> Reconcile["Deduplicate or record relationship"]
    Reconcile --> Index["Index eligible knowledge"]
    Index --> Retrieve["Retrieve within context budget"]
    Retrieve --> Revalidate["Revalidate supporting sources"]
```

Deterministic observations are recorded synchronously: command exit codes, read file hashes, environment fingerprints, changed files. Task-state updates are also synchronous. Optional LLM extraction runs only after an operation settles or a phase completes; do not pay an extraction call for every token or file read.

Extraction uses the prescribed task model and shared budget. Its output is a candidate MemoryRecord plus cited source IDs. Validate that the sources exist, are in scope, and contain the claimed supporting passage or observation. A source link alone does not prove an inference correct. Store inferred explanations as hypothesis or derived, not observed.

Extraction may fail without failing the coding task. Its completion cannot mark a criterion satisfied, amend a permission, or replace the original task. Background jobs carry a source watermark so stale jobs cannot overwrite newer knowledge.

## Identity, relationships, and conflicts

Each atomic record describes one fact with enough context to interpret it. fact_key groups claims about the same entity/property within a scope, such as the test command for a package and toolchain version. Stable source IDs and normalized text prevent repeat ingestion from creating copies.

Supported relationships:

- supersedes: a fact about the same subject/property is replaced under compatible scope and supporting evidence.
- extends: additional detail complements a fact without invalidating it.
- derived_from: a conclusion depends on other records; it retains the inferred evidence category.

Use relational tables, not a separate graph database. Reject cross-scope relationships without explicit allowed scope access. Supersedes chains and derivation dependencies must be acyclic. Invalidating or forgetting a source invalidates dependent eligibility and materialized profiles.

“Newest wins” is insufficient. A newer guess does not supersede an observed value; a change on another branch does not update the current branch. A direct current-file observation can supersede an older observation of that file. Incompatible claims with insufficient evidence remain separate and are surfaced as unresolved conflicts.

Example: a successful test command is observed under one lockfile hash. After dependencies change it becomes stale. It may still be useful historical evidence, but the engine cannot report that the current test environment is working without rerunning it.

## Scoping and evaluation independence

Access is checked before query ranking, profile construction, relation expansion, export, and deletion.

- A session sees its own task state and permitted repository knowledge.
- Repository knowledge is tied to repository identity, workspace/revision applicability, and supporting hashes.
- Read-only workers receive the parent's explicit scope subset and snapshot references.
- User preferences are product-only unless explicitly provided as task input.
- Evaluation tasks use fresh task-specific knowledge namespaces; no prior benchmark solutions or user profile are injected.

Resume of the same evaluation task retains its own memory. Starting a different evaluation case resets reusable knowledge by default. The official policy may later permit broader reuse; that requires an explicit profile change and benchmark disclosure.

Scope identifiers organize and enforce access in Ion's data layer; naming strings alone do not create an OS or multi-tenant security boundary.

## Lifecycle and freshness

| Transition | Trigger | Retrieval effect |
| --- | --- | --- |
| active → stale | Supporting file/environment changed, source missing, or applicability cannot be established | Excluded from factual context; may be shown as a labeled historical lead on request. |
| active → superseded | Valid replacement with same applicable subject/property | Default queries select replacement; history remains auditable. |
| active → expired | Explicit valid_until passed | Excluded from current context. |
| any → forgotten | Explicit memory-forget request | Tombstone; remove from FTS/profile/caches and prevent automatic re-extraction from the same source. |
| stale → active | Fresh observation supports the claim again | Record new evidence/time; never merely refresh a timestamp. |

File-backed facts are validated by hashes, not branch names alone. Command recipes depend on relevant manifests, lockfiles, runtime version, and working directory. A hash change invalidates eligibility conservatively; unchanged dependencies can preserve a fact across commits.

Branch switches, resume, and verification trigger explicit revalidation. Before presenting actionable facts for the next edit, recheck their support. External edits can race a check; patch preconditions remain the final protection.

## Retrieval

V1 retrieval combines a small explicit profile with query-driven facts and direct repository tools. The stable profile contains user-confirmed preferences and currently valid repository essentials. Dynamic context contains current task state and recent unresolved work.

Construct the query from task intent, current phase, next action, implicated paths/symbols, and error signatures. Do not use only the last user sentence.

Retrieval sequence:

1. Compute allowed scopes and applicability filters.
2. Select active, nonexpired records and the bounded stable profile.
3. Retrieve lexical/FTS5 candidates using paths, symbols, and prose.
4. Prefer exact identifiers and valid observed support; use FTS relevance within comparable evidence classes, with stable ID tie-breaking.
5. Deduplicate facts shared between profile and search, revalidate support, and include citations/evidence labels.
6. Pack candidates into the knowledge allocation from the context budget; record omitted candidates and reasons.

An empty or timed-out result falls back to repository search. It does not trigger speculative fact generation. Vector search, graph-wide inference, and learned rerankers are deferred until their resolution-rate benefit exceeds their latency and resource cost.

## Retention, forgetting, and privacy

Task evidence persists until an explicit future artifact/session deletion operation. make clean does not erase it. Knowledge expiry removes retrieval eligibility without erasing historical task records.

Forgetting a fact removes it from active retrieval and profile views and invalidates derivations. It does not erase a transcript/file containing the original statement. A tombstone suppresses re-extraction of that fact from the same existing source; a new explicit user statement can create a new record with a recorded reason.

Generated summary exports are readable Markdown under the private artifact store. Do not automatically write MEMORY.md into a target repository, overwrite a user's existing memory file, or sync code to a hosted provider.

Store no API keys or known secret values. Redact before persistence as described in [security](security.md). Local databases are not encrypted in v1; explain this limitation before storing sensitive product data.

## Interfaces and observability

MemoryStore exposes observe(candidate), query(scope, query, budget), invalidate(source_ref), forget(memory_id), and profile(scope). Each returns typed results and source identifiers, never permissions.

Record query latency, cache hits, retrieved/selected token counts, invalidated facts, contradictions, extraction requests, and retrieval failure reasons. Measure factual usefulness through downstream task outcomes and stale-fact tests, not just recall on stored prose.

Required scenarios: changed build command, conflicting branch facts, failed extraction, forgotten fact re-ingestion, user preference isolation, stale derivation, and repository scope leakage. See EVAL-09 in [evaluation](evaluation.md).
