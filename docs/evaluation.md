# Evaluation and release verification

Status: validation reference. Offline checks are shipped; organizer-specific live evaluation remains gated by [rules](rules.md).

## Test layers

1. Contract/unit checks validate schemas, state transitions, budgets, scopes, and deterministic selection.
2. Integration checks use real temporary repositories, files, process groups, and SQLite transactions. A scripted provider supplies deterministic model events; it is not a replacement for live-model evaluation.
3. Fault-injection checks interrupt the engine at intent, side effect, artifact, settlement, and compaction boundaries.
4. Live task benchmarks run the locked model against fixed repository/task revisions, with an independent grader and a recorded budget.
5. Submission checks reproduce the official environment and Makefile sequence at the actual submitted revision.

Do not write tests that merely restate a mocked response. For example, recovery must inspect an actual partially changed filesystem, and process cancellation must prove the descendant process terminated.

## Required scenario matrix

| ID | Requirement coverage | Scenarios and required observation |
| --- | --- | --- |
| EVAL-01 | HK-01–03, HK-09, HK-11, HK-13 | Clean checkout runs setup, offline tests, and launch; rerun setup is idempotent; no source edits/manual fixes; key unnecessary for setup/test. |
| EVAL-02 | HK-03, HK-08 | TUI launch via make run, interactive task text entry/paste, target selection, clear non-TTY launch failure, UI detach/reattach, session inspection without model calls. |
| EVAL-03 | HK-04–05 | Missing/invalid key, known secret echoed by a fixture, subprocess environment capture, provider error dump, tracked-file/history scan; no secret reaches child env or retained output. |
| EVAL-04 | HK-06–07 | Primary/worker/compactor/extractor all use locked text model; reject repository/user config model override; native and structured-action protocols; reject media-dependent inputs and malformed actions. |
| EVAL-05 | Ion workspace policy | Dirty index/worktree, new files, deletion, symlink escape, traversal, non-Git inspection, external edit after read; unrelated external edits excluded from Ion patch; same-file/command overlap marked ambiguous; preserve user changes and reject stale patches. |
| EVAL-06 | Ion process policy | Invalid tool arguments, large Unicode output, huge single line, quota exhaustion, process timeout, unexpected interactive subprocess prompt, background readiness failure, descendant cancellation, cursor pagination. |
| EVAL-07 | Ion recovery policy | Crash before/after intent; command side effect before settlement; multi-file partial patch; PID reuse; session A crashes during a writing command and session B immediately starts; spawn gate/owner-loss cleanup; missing/corrupt artifact; interrupted checkpoint. Never blindly replay unknown writes or admit a second writer around an orphan. |
| EVAL-08 | Ion context policy | Small context limit, repeated compaction, post-intake non-criterion constraints and steering during summary generation, lost-summary constraint attempt, orphaned tool result, provider-native epoch metadata, failed compactor, one overflow repair, pinned content too large. |
| EVAL-09 | Ion memory policy | Cross-repo/branch facts, changed lockfile, contradictory observations, inferred fact labeling, stale derivation, forgotten fact re-ingestion, scope leaks, duplicate injection, retrieval timeout. |
| EVAL-10 | Ion verification policy | Fabricated evidence IDs, unrelated passing tests, zero tests collected, failing baseline, new regression, post-test edit, service cleanup modifies source, unavailable check, no-op task, valid static/observation evidence without fabricated commands, kind-specific missing-source rejection, patch attribution and final report accuracy. |
| EVAL-11 | Ion budget/worker policy | Concurrent budget reservation, retry charges, worker timeout, same-model enforcement, attempted recursive delegation/write, stale worker snapshot, valid polling versus loop, pause/cancel, exhausted finalization reserve. |
| EVAL-12 | HK-12 | Cleanup removes enumerated disposable artifacts only; preserve target files, sessions, user logs, patches, symlinks to external locations. |
| EVAL-13 | Ion security policy | AGENTS/CLAUDE precedence, instructions in logs/memory, repo capability escalation, model lock bypass, worker artifact scope, private socket permissions, no public listener. |
| EVAL-14 | HK-10 | Manifest/configuration capture, model usage including auxiliary calls, unknown usage reporting, baseline/ablation comparison, reset of evaluation memory, independent grading. |

All critical offline cases must pass before calling a milestone complete. Passing them establishes tested behavior, not universal correctness or immunity to malicious code.

## Offline suite contract

`make test` runs schema/unit, repository/process integration, and scripted end-to-end scenarios without network or credentials. Tests use isolated temporary directories and must never operate on the developer's real home/repository as a destructive target.

Tests live under `tests/` and are grouped by runtime concern. Provider simulation emits tool calls, transient errors, malformed JSON, usage reports, and context-overflow signals in controlled order. Use [agile](agile.md) to plan new scenarios.

Process tests run on each supported OS. If the actual evaluation OS cannot support a required process-control guarantee, resolve OPEN-02 before release rather than skipping the test silently.

## Benchmark manifest

Each case records case ID, task text, repository URL/local fixture identity, base commit, initial patch if any, provisioning recipe, checks, protected expected behavior, allowed execution/network policy, and resource limits. Hash the manifest and grader version.

The agent sees the task and allowed repository. Hold-out expected patches/tests and grading logic live outside its tool scope. Running the evaluator through the same writable workspace as the agent does not provide independent grading.

Begin with at least 12 development cases spanning Python and JavaScript/TypeScript repositories: localized bugs, multi-file changes, regression tests, unfamiliar build layouts, missing dependencies, and environmental failures. Add a disjoint hold-out set of at least 12 cases before tuning workers/retrieval. These are team benchmark sizes, not official hackathon task counts.

For each candidate, run at least three attempts per case where API budget permits. If only one attempt is affordable, report that limitation. Avoid claiming superiority from a single favorable example.

## Metrics and experiment gates

| Metric | Definition |
| --- | --- |
| Resolution rate | Independently passing cases / attempted cases, with failures included. |
| False-success rate | Self-reported verified cases that fail independent grading / all self-reported verified cases; report denominator and count. |
| Tokens per resolved task | Total tokens for all attempts, including failures and auxiliary calls, divided by independently resolved tasks. Undefined when none resolve. |
| Latency | End-to-end task time; report p50/p95 with sample size and budget timeouts. |
| Recovery success | Injected recoverable failures that safely resume and reach the expected result / injected recoverable failures. |
| Tool failure rate | Invalid/failed tool operations by category; distinguish expected test failures from malformed calls. |
| Context overhead | Retrieval/extraction/compaction tokens and duration plus memory selected/invalidated counts. |

Use paired comparisons on the same cases, model profile, environment, and budget. Report absolute counts, per-case changes, and uncertainty (for example a Wilson interval for proportions); small samples are exploratory.

Ablations: baseline only; plus durable recovery/verification; plus memory/context; plus workers. Disable reusable cross-task memory in evaluation unless permitted. A warm-memory product experiment must be labeled separately from cold-task competition results.

Enable workers by default only if held-out results improve resolution or reduce resources without a resolution regression, and add no critical false-success, secret-leak, or state-corruption failure. Ambiguous evidence leaves the feature opt-in.

Do not report cached tokens as zero total usage, omit failed attempts from costs, or describe a deterministic fixture as a live-model benchmark. Costs are estimates only when profile pricing is known.

## Clean-environment release procedure

1. Resolve and record all OPEN items from [rules](rules.md).
2. Pin runtime, dependencies, bootstrap checksums, official model profile, and effective budgets.
3. Obtain a fresh copy of the candidate submission in the actual prescribed environment.
4. Inject AI_API_KEY externally; run make setup, make run, and make test.
5. Supply an official-format task and inspect its output location and independently graded result.
6. Exercise the TUI path, restart/recovery through the TUI, and cleanup safety.
7. Scan committed files and history for credentials; verify no additional secret/service is required.
8. Save a release report containing revision, manifest/profile hashes, commands, exit codes, environment, evidence, and unresolved limitations.

The harness must be installable through the standard entrypoint. A project running only in the author's already-provisioned environment is not release-ready.

## Documentation-phase verification

For documentation changes, verify document inventory, relative links/anchors, unique requirement IDs, consistent schemas/defaults, and Mermaid syntax. Review semantic failure modes separately. These checks do not satisfy the runtime scenario matrix above.
