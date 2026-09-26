# Ion



Ion is a terminal coding harness for the AI Harness Hackathon 2026. It reads text tasks, inspects local repositories, applies guarded edits, runs bounded commands, and reports changed files with verification evidence.

## Start

Requires a terminal and Python 3.12 or newer. From this repository:

```sh
make setup
export OPENROUTER_API_KEY="<your key>"
make run
```

The default development profile is `openrouter-coding-free` (Cohere North Mini Code via OpenRouter), which completed a live small bug-fix test. Launch `ion` from the repository you want to edit; that directory becomes the immutable workspace for the process. `/doctor` checks the active credential, endpoint, model, tool support, live limits, and OpenRouter free quota. `/logs` shows the recent internal request, tool, and budget sequence. `/models` lists profiles and, when a key is available, discovers selectable provider models. `/history` shows saved runs; `/inspect TASK_ID` shows their details. `/steer TEXT` adds an instruction to a running task at its next model turn. `make test` runs the offline suite. `make clean` removes disposable build and test caches.

## Terminal interface

Ion uses a compact workbench layout built around a task dock, session timeline, and run-state rail. The interface is designed for JetBrains Mono; select that font in your terminal profile before launching Ion. Textual inherits the terminal emulator's active font and cannot replace it from application CSS.

| Action | Shortcut / command |
| --- | --- |
| Send task / steer a running task | Enter |
| Insert newline | Shift+Enter or Ctrl+J |
| Search commands | Ctrl+P or `/help` |
| Choose model | Ctrl+X, then M or `/models` |
| Show locked workspace | Sidebar or bottom status bar |
| Connect a configured provider | `/connect` |
| Inspect saved tasks | `/sessions` or `/history` |
| New task view | Ctrl+N or `/new` |
| Toggle context sidebar | Ctrl+B |
| Cancel active task | Escape |
| Quit | Ctrl+Q |

The sidebar hides automatically in narrow terminals. Session transcripts and highlighted diffs reflow when the terminal is resized. Sessions are journaled for inspection and `/resume TASK_ID` performs recovery checks before preparing a safe re-submission; it never replays an old mutation. Each submitted task starts a foreground engine run; messages sent while it is running are steering instructions.

`/connect` offers the providers configured in `ion.toml`. Its masked input keeps the key in the current process only and does not write credentials to disk. Catalog access or the next request checks whether the key works. Existing environment configuration remains available. OAuth and additional provider protocols are separate work; matching the dialog layout does not add those capabilities.

## Choose a provider

The committed [ion.toml](ion.toml) contains Groq Qwen, OpenRouter coding, Qwen, and free-router profiles, plus direct DeepSeek and Qwen API examples. Export the matching key:

| Profile | Credential |
| --- | --- |
| `groq-qwen-dev` | `GROQ_API_KEY` |
| `openrouter-coding-free`, `openrouter-qwen-free`, `openrouter-free-router` | `OPENROUTER_API_KEY` |
| `deepseek-direct` | `DEEPSEEK_API_KEY` |
| `qwen-direct` | `DASHSCOPE_API_KEY` |

The direct provider APIs may require a paid account. A `:free` OpenRouter model is subject to provider availability and rate limits. Catalog availability is checked live; these profiles are examples, not a promise that every model remains free or available.

For local use, copy `.env.example` to `.env` beside the active `ion.toml` and fill in the key for the provider you selected. Ion loads that file without overriding environment variables already set by the shell. Set `ION_ENV_FILE` to use a different local file. Locked evaluation mode skips dotenv and reads only the externally provided `AI_API_KEY`.

To connect another OpenAI compatible text model, create a TOML file outside the target repository with `schema_version = 1`, `default_profile`, and a `[profiles.NAME]` section. Specify `provider`, `base_url` (HTTPS), `model`, `api_key_env`, `protocol = "openai_chat"`, `tool_protocol = "native"` or `"structured_json"`, `text_only = true`, `locked = false`, `context_window`, and `max_output_tokens`. Launch with `ION_CONFIG=/path/to/your.toml make run`. A provider specific key is preferred; `AI_API_KEY` is the fallback in normal use. Never place key values in TOML or Git.

## Small tasks and token budget

Restart Ion after changing `.env` or the default profile. Start with a specific task naming the file and expected behavior. The currently running TUI retains its selected model until you change it through `/models` or restart.

Product runs default to economy mode: **read → brief plan + edit → bounded check → final diff and evidence**. The TUI enables eight tools, including the policy-checked command runner:

| Tool | Purpose |
| --- | --- |
| `repo_list` | List files within a directory, with pagination |
| `repo_search` | Find literal text with a path filter and source offsets |
| `file_read` | Read a bounded page and obtain a guarded read ID; optional `limit` up to 16,000 characters |
| `edit_file` | Apply an exact replacement in observed text |
| `write_file` | Create a file (including missing directories), or rewrite a fully read file without repeating old text |
| `diff_inspect` | Inspect accumulated changes when needed |
| `command_start` | Run one bounded repository check with a clean environment and retained output artifact |
| `finish_request` | Finish or report a blocker honestly |

Both edit tools require a short plan, displayed before execution. `done=true` ends a successful edit without another model request; use `done=false` to continue across files. Reads and searches stay available after edits. Existing files require current read IDs; whole-file replacement also requires reading all pages first. Hash checks reject stale edits and creation never overwrites an existing file. File deletion is unavailable. Product mode permits one bounded command at a time; destructive commands, shell chains, redirection, private files, and API-key environment variables are rejected.

For a task naming one existing file, Ion can inspect up to 12,000 characters locally before its first model request, provided the source fits the context budget. An explicit whole-file rewrite with complete observed source directs native tool selection to `write_file`. This removes model calls spent locating and rereading a known target. Larger files and tasks across files keep normal paginated inspection. If the provider rejects directed selection, Ion makes one attempt using automatic selection.

The workspace is captured from the launch process's current directory and cannot be changed through `/repo` or `ION_REPO`. File tools reject absolute paths, parent traversal, and symlink targets. Commands run in that workspace with a filtered environment and process-group cleanup; they cannot access files outside it through the harness.

Search supports an optional `relative_path` and returns character offsets for reading the surrounding code directly. A command only verifies a task when its output identifies a relevant passing check and the final workspace fingerprint is unchanged. Diff capture records what changed; it does not prove correctness.

Diagnostics are appended to `$ION_DATA_DIR/logs/ion.jsonl`, defaulting to `~/.local/share/ion/logs/ion.jsonl`, and rotate at 2 MB. They include phases, offered tool names, token accounting, safe path/offset metadata, tool status, retries, and outcomes. They exclude credentials, prompts, search text, source text, patch contents, and model tool arguments. Use `/logs` or `/debug` in the TUI to inspect the latest events.

Configure `[economy]` in `ion.toml`: `enabled = true`, `max_requests = 12`, `max_total_tokens = 24000`. Each request reserves estimated input plus its output cap; complete provider usage replaces that reservation when available. This is an estimated admission limit, not an exact tokenizer or provider billing ceiling. Failed requests and retries consume budget. One repair attempt is allowed for invalid actions/tool failures, and at most one consecutive rate-limit retry. Saved results include request counts, reported input/output tokens, and accounted tokens. Set `enabled = false` to restore the legacy tool workflow; locked evaluation mode uses that workflow independently.

The default coding profile allows up to 4,096 output tokens. Economy requests start at 1,024 tokens before reading and 2,048 afterward, bounded by the profile limit; explicit rewrites start at the full profile limit. A truncated response triggers one retry at the profile limit; partial tool calls are never executed. Provider usage is retained even when an action is truncated or malformed. Logs include the stop reason and reported reasoning-token count. Every profile defaults to an estimated 6,000 input tokens per request, including tool schemas; customize `input_budget_tokens` in trusted TOML if needed. Estimates use serialized character counts, not a model-specific tokenizer. Older complete tool turns are dropped together; pinned task instructions and the latest tool turn are retained. Oversized required context stops the task instead of silently dropping instructions.

To spend provider quota on an isolated live check, run `uv run python scripts/smoke_economy.py` from the Ion source checkout. It submits the exact task `rewrite the readme` against a temporary README copy, prints safe diagnostic events, and leaves the working repository untouched.

Ion keeps bounded working memory in each run's artifact directory and stores reusable, source-linked repository memory in its local data directory. Compacted prompts receive pointers instead of replaying old source/log output; stale file references are marked for rereading. Repeated tool cycles trigger a warning after three repetitions and stop after four without workspace progress. See [context management](docs/context-management.md) and [memory architecture](docs/memory-architecture.md) for the runtime contracts.

File reads return 4,000-character pages; economy prompts receive a short read ID instead of the full-file hash. Listing/search results and command feedback are bounded. Economy runs use the limits above; legacy runs have a 24-request ceiling including a verification reserve. Both have a ten-minute admission deadline. The activity view shows request counts and token usage. Free endpoints can still be rate limited; changing providers or models requires explicit selection.

File-read activity includes the path and character offset. Equivalent reads of the same unchanged page are counted even when the model varies its call arguments. The controller supplies the next-page offset and directs the model toward a patch; five reads of the same unchanged page stop the run. Older duplicate page bodies and obsolete file versions are replaced with metadata, while distinct pages remain available within the context budget.

Live smoke result (2026-09-27): the default model fixed subtraction to addition in a disposable Python repository via the TUI Run button, preserved all tests, and passed three tests. Ion returned `verified` with one verification record. That run used eight requests and reported 5,804 input / 698 output tokens. This establishes a small-task baseline, not general issue-solving reliability. The verification observer recognizes focused pytest, unittest, npm/pnpm/yarn, cargo, and go checks; documentation-only edits remain unverified unless a relevant executable check exists.

## Hackathon evaluation

The Makefile exposes `make setup`, `make run`, `make test`, and `make clean`. The evaluator can export `AI_API_KEY` before launch. Once the committee gives the exact provider, model, and endpoint, add a profile with `locked = true` and set `evaluation_profile = "NAME"` in `ion.toml`. That mode reads **only** `AI_API_KEY` and disables model switching. The announcement reported Qwen and DeepSeek model families; the exact official model IDs and credential provider are still required to freeze an evaluation profile. The project does not claim official submission readiness until those are confirmed and a live end to end run succeeds.

Ion executes repository commands on the local machine. Use it on repositories you trust. Tool output, patches, and run history are retained under the user's Ion data directory. The foreground TUI records operation intent before dispatch, uses a durable workspace admission claim, exposes reconnectable session event primitives, and wires source-linked memory plus atomic compaction checkpoints into runs. Detached client-independent execution remains a future increment; current runs stay attached to the foreground TUI. See the [agile delivery guide](docs/agile.md) and [hackathon rules](docs/rules.md) for the remaining release gates.

See [the product documentation](docs/README.md), [hackathon rules](docs/rules.md), and [architecture](docs/architecture.md).
