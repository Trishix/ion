# Hackathon rules and compliance contract

Status: organizer rules transcribed; a foreground implementation exists, while final compliance checks are incomplete.

This is Ion's authoritative transcription of the organizer requirements supplied by the user on 2026-09-26. Source labels below refer to the numbered sections of **AI Harness Hackathon 2026 — Standardised Makefile-Based Evaluation Setup**, and the supplied problem statement. No public organizer URL or separate scoring rubric was provided. The duplicate copies in the conversation are one source, not two independent rule sets.

The teammate's PDF is a technical proposal, not an organizer amendment. Later official instructions supersede this transcription only after their source and resulting changes are recorded here. Do not silently convert an assumption into a rule.

## Organizer requirements

MUST below denotes an explicit organizer obligation. SHOULD denotes guidance qualified by phrases such as “where applicable” or “to the extent reasonably practicable.”

| ID | Strength and requirement | Supplied source | Implementation owner | Release validation |
| --- | --- | --- | --- | --- |
| HK-01 | MUST place a Makefile at the submitted repository root and expose setup, run, and test targets. | §§1, 5, 12–14 | Packaging | Fresh checkout contains the root file and all three targets. |
| HK-02 | MUST make setup install/configure the declared execution dependencies; setup must succeed. | §§1, 5, 9, 13–14 | Packaging | EVAL-01 in a clean environment; no undocumented manual installation. |
| HK-03 | MUST make run initialize and launch the harness in its intended evaluation mode; launch must succeed. | §§1, 5, 12–14 | TUI/session service | EVAL-01, EVAL-02. |
| HK-04 | MUST read the supplied runtime credential from AI_API_KEY without editing source. | §§2, 4–5, 8, 12 | Model gateway | EVAL-03 with injected credential; missing-key error contains no credential. |
| HK-05 | MUST NOT hard-code or commit credentials in source, Makefiles, configuration, documentation, or .env files. A blank .env.example is permitted. | §§2, 8 | All components | EVAL-03 plus tracked-file/history secret scan before submission. |
| HK-06 | MUST use text-only language models for evaluation and accept text evaluation input without image, audio, video, or other multimodal requirements. | §3; problem statement | Gateway/input adapters | EVAL-04 inspects every model request and task input path. |
| HK-07 | MUST clearly define the model configuration and use the prescribed model/family if specified; no unauthorized substitution. | §4 | Gateway/configuration | EVAL-04 checks primary, worker, extraction, and compaction calls. |
| HK-08 | MUST launch a TUI through make run if providing a TUI; no hidden team-specific initialization command. | §6 | TUI/packaging | EVAL-02 on a supported terminal. |
| HK-09 | MUST encapsulate routine setup; evaluators should not have to change source/dependencies/configuration or contact the team to run the submission. | §§9, 11–14 | Packaging/release | EVAL-01 with only the officially supplied environment and credential. |
| HK-10 | SHOULD control/document randomness and execution settings affecting results, to the extent reasonably practicable. | §10 | Configuration/evaluation | EVAL-14 records effective settings, software versions, seed support, and budgets. |
| HK-11 | MUST expose the team's test/evaluation procedure through make test; evaluators may run it where applicable. | §§1, 5, 12–13 | Evaluation | EVAL-01 executes the offline suite successfully. |
| HK-12 | SHOULD provide make clean to remove generated artifacts where applicable; the command appears in the organizer command table. | §1 | Packaging | EVAL-12 confirms only enumerated disposable artifacts are removed. |
| HK-13 | MUST verify setup and launch from a clean environment before final submission; verify tests where applicable. | §§13–14 and final requirement | Release | Retain dated EVAL-01 report for the actual submission revision. |

The stated minimum executable interface is successful setup and launch. This does not remove the requirement to expose make test. Ion will implement all four targets, including clean.

The problem statement asks for autonomous repository navigation, tool use, context management, model orchestration, recovery, resource efficiency, and correct verified changes. It does not mandate a framework, multi-agent topology, Docker, a vector database, or a particular interface design. It does not provide numerical scoring weights or success thresholds.

## Ion engineering policies — not organizer rules

| ID | Policy | Reason |
| --- | --- | --- |
| POL-01 | Use Python, a local durable engine, and a TUI-only user interface. | Agreed product direction; other user-facing interfaces are out of scope. |
| POL-02 | In evaluation, all generative calls use the locked prescribed model; no external embedding or memory service is required. | Avoid hidden credentials and model substitutions. |
| POL-03 | Isolate reusable cross-task memory in evaluation; start each independent case with fresh memory. | Conservative fairness default pending official policy, not an asserted prohibition. |
| POL-04 | Require recorded verification for a verified result; preserve partial results otherwise. | Prevent unsupported success claims. |
| POL-05 | Keep the model credential out of repository subprocess environments. | Minimize accidental disclosure. This alone is not OS isolation. |
| POL-06 | Require make test to work offline and without an API key; live model evaluations are separate opt-in runs. | Reliable submission diagnostics without consuming inference quota. |
| POL-07 | Make clean preserve sessions, patches, user files, and target repositories. | Avoid destructive cleanup and loss of evidence. |
| POL-08 | Use one repository writer; bounded read-only workers share the primary task's budget. | Preserve edit ownership and cost accounting. |

Policy details and numerical development defaults are owned by [interfaces-and-data](interfaces-and-data.md). They are not official evaluation limits.

## Unresolved official details and release blockers

| ID | Missing information | Current planning assumption | Required resolution |
| --- | --- | --- | --- |
| OPEN-01 | Model, provider protocol, endpoint, limits, and tool-calling capability | Provider adapter boundary; no invented model ID | Obtain official specification, commit nonsecret evaluation profile, validate all model paths. |
| OPEN-02 | OS, architecture, installed runtime/tools, and setup network access | Linux x86-64 evaluation candidate; macOS local development; setup network available | Reproduce the actual environment; pin working runtime/dependency versions. |
| OPEN-03 | How the evaluator supplies task text and target-repository location to the TUI | TUI text entry/paste and explicit repository selection | Add the official input adapter within the TUI and ensure make run works without source edits. |
| OPEN-04 | Time, tokens, API quota, cost, and scoring policy | Development defaults only | Configure official limits and budget accounting; do not claim an unofficial score. |
| OPEN-05 | Dependency-installation and execution network policy | Trusted local execution; optional container backend | Validate needed provisioning and tool permissions against official infrastructure. |
| OPEN-06 | Reusable memory, external tools, and additional-model policy | Fresh cross-task memory; no additional inference service | Confirm allowed behavior and record the approved configuration. |
| OPEN-07 | Submission deadline, packaging, and artifact handoff expectations | Git repository plus patch/result artifacts | Confirm submission procedure and task-result location. |

OPEN-01 through OPEN-07 block claims of submission readiness, not architecture work or offline implementation. Do not shift their resolution to the evaluator.

## Evaluator contract

The documented official sequence is: obtain repository, enter its root, export AI_API_KEY externally, run make setup, run make run, supply the official issue/test case in the launched TUI, and optionally run make test. There must be no interactive login, key copied into a file, or second service credential in this path. The TUI is the only user-facing task interface; organizer-mandated Makefile targets remain the packaging/evaluation entrypoint, not a second product interface.

The root README shows the sequence without a real credential. The blank .env.example also lists optional provider-specific variable names for local product use; official evaluation still requires only AI_API_KEY.

Submission compliance requires evidence from the final submitted revision. A documentation review does not establish runtime compliance. See [evaluation](evaluation.md) and [implementation-plan](implementation-plan.md).
