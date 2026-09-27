# Security and trust boundaries

Status: runtime security boundary and limitations. Controls are implemented where noted; trusted-local execution is still an explicit assumption.

## Scope and assumptions

V1 runs on a developer/evaluator machine against trusted local repositories. Repository tests, build scripts, hooks, dependencies, and shell commands are executable code. The local backend is not suitable for hostile repositories or mutually untrusted tenants.

Capability checks govern what Ion dispatches; they cannot prevent an allowed subprocess from using the privileges of the host user. A Git worktree separates changes, not security authority. Running without the model key in a child's environment reduces accidental leakage but does not protect against malicious same-user process inspection.

Untrusted-code isolation requires a container/VM boundary designed and validated separately. This distinction also appears in OpenCode's [security model](https://github.com/anomalyco/opencode/blob/b65de4d6943ef35337f8f2bfdbb369f6d25e7e9f/SECURITY.md); adopting its permission concepts does not create a sandbox.

## Assets and boundaries

| Asset | Main threat | V1 control and limitation |
| --- | --- | --- |
| AI_API_KEY | Logging, inheritance, accidental source disclosure | Gateway-only use; scrub child environment and logs; no same-user hostile-code guarantee. |
| User repository changes | Stale writes, destructive recovery, unsafe cleanup | Captured baseline, exact hashes, guarded patching, no implicit Git reset/stash. |
| Task evidence | Model fabrication, tampering, corruption | Controller-owned records, artifact hashes, private data directory; not tamper-proof against host owner. |
| Reusable knowledge | Cross-project leakage, stale facts, prompt injection | Scope enforcement, provenance, invalidation, data labeling. |
| Local control socket | Unauthorized session control | Owner-only directory/socket, no public TCP listener by default. |
| Provider traffic | Wrong endpoint/model or accidental extra service | Explicit committed evaluation profile, HTTPS validation, no silent fallback. |

## Capabilities and approval policy

Capabilities distinguish repository reads, guarded edits, command execution, managed artifacts, network-enabled tools, and delegation. Effective authority is the intersection of trusted user configuration, session mode, role, and locked evaluation profile. Repository instructions/configuration cannot grant capabilities.

Trusted-local product mode preauthorizes ordinary in-scope file edits and configured repository tests/builds. Publishing, pushes, deployment, credential access, writes outside scope, and broad destructive operations require explicit user direction and an appropriate implemented capability; they are not automatic coding steps.

In the TUI, an action needing new authority returns a policy blocker with a concrete explanation and available safe choices. The agent never silently approves itself or waits forever. Evaluation profile permissions must be resolved before submission to support the official tasks without hidden prompts.

Workers cannot widen authority, use parent-only tools, read unrelated scopes, or delegate recursively. Permission checks are repeated at execution time, not only when tool schemas are shown.

## Secrets and provider access

- Read AI_API_KEY from the runtime environment; never serialize it into TaskSpec, profiles, events, crash reports, or examples.
- Keep credential handling inside the gateway and strip known secret environment variables before spawning commands.
- Redact exact known secrets and common credential patterns before artifact/journal persistence and before rendering output. Avoid logging authentication headers or full error request dumps.
- File/search tools deny common secret files by default unless an explicitly authorized task needs them; even then never send known credentials to the model.
- Retain no credentials in .env files. A committed .env.example, if later added, contains empty values only.
- Verify TLS certificates. Never work around provider errors by disabling verification.

Pattern matching cannot identify every secret. Product documentation must describe what content is sent to the selected model and how local logs are retained. No hosted memory sync or telemetry upload is enabled by default.

## Instructions and memory injection

Task input, repository instructions, retrieved facts, tool output, and external documents have explicit provenance. Logs that say “ignore your instructions” remain log data. A remembered command is an advisory recipe, not authorization to run it.

Context serialization escapes managed delimiters and separates retrieved data from instructions. It is a mitigation, not a proof of prompt-injection immunity. Enforcement still occurs outside the model: path bounds, role permissions, model lock, budget limits, and completion evidence.

Agent modifications to instruction/configuration files are visible in the final diff. Re-reading a changed file must not expand the authority granted by the original trusted profile. Review unexpected modifications to tests, configuration, and instructions before finalization.

## Files, artifacts, and cleanup

Canonicalize paths, check symlinks at access time, and operate through the repository/managed-artifact APIs. Recognize races and platform limitations; do not claim local path checks stop malicious shell code.

Artifacts have hashes and explicit completeness/redaction metadata. Restrict local data permissions. V1 data is not encrypted at rest. make clean removes only known disposable build/test paths owned by Ion, never a caller-supplied directory, repository, session database, or patch archive.

Memory forget excludes a fact from retrieval but does not erase all copies of its source data. Source deletion requires a separate explicit lifecycle operation and must invalidate all dependent references; see [memory-architecture](memory-architecture.md).

## Optional container backend requirements

When implemented, run repository execution as an unprivileged user with restricted mounts, no host Docker socket, bounded CPU/memory/processes, and explicit network settings. Model requests remain in the gateway outside that execution environment.

Provision dependencies before a network-disabled task phase or through a separately authorized provisioning phase. Do not pass AI_API_KEY into the task container. A requested isolated backend failing to start is an error, not permission to execute locally.

These requirements define an extension acceptance boundary; no container implementation is included in the v1 competition baseline.

## Validation and disclosures

EVAL-03 tests secret propagation and redaction. EVAL-05 and EVAL-12 test path/patch/cleanup safety. EVAL-13 tests malicious retrieved instructions, worker authority, model override attempts, and socket/file permissions.

The final product README must disclose trusted-local execution, model data transmission, local retention, unencrypted storage, and optional isolation. Actual sandbox/security claims require separate implementation and adversarial verification.
