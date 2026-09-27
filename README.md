# Ion

Ion is a local, terminal-based coding agent. Give it a task in its Textual interface; it inspects the current repository, makes guarded changes, runs bounded checks, and reports what changed and what it verified.

## What Ion does

Ion connects a configured language model to a local coding workflow. It keeps repository access and task execution under the harness, while sending selected task context and source text to the provider you choose.

Features include:

- Output-aware token budgets that reserve room for useful edits, checks, and a final response.
- Progressive, bounded tools for repository search, paged reads, edits, artifact lookup, and change summaries.
- Path and hash checks that reject stale or out-of-workspace edits.
- Bounded command execution with retained output and verification evidence.
- Session and operation records that support inspection and cautious recovery without replaying old side effects.
- A terminal workbench for task input, steering, model selection, diagnostics, and review of changes.

## Why use Ion

Ion is designed to keep small coding tasks focused: name a file and desired behavior, let Ion gather only the needed context, then review its diff and verification result. Context selection trims optional information before required task details, and the tool set grows only when the task has evidence that needs it. The budget view and result distinguish a prompt that cannot fit from an exhausted request or token limit.

Ion is a local harness, not an operating-system sandbox. See [Security](docs/security.md) before using it with repositories or commands you do not trust.

## Get started

### Requirements

- Python 3.12 or 3.13
- `make`
- An API key for one of the configured providers
- An interactive terminal

The setup target bootstraps `uv` if needed, then installs the locked project environment.

### Install and configure

```sh
git clone https://github.com/Trishix/ion.git
cd ion
make setup
cp .env.example .env
```

Add the key for your selected provider to `.env`. The default profile is `openrouter-coding-free`:

```dotenv
OPENROUTER_API_KEY=your-key
```

You can set the key in your shell instead. Ion does not replace an environment variable that is already set. Never commit `.env` or put key values in `ion.toml`.

### Launch Ion

To work on the Ion checkout itself, launch from its directory:

```sh
make run
```

Ion treats the directory where it starts as the workspace. To work on another repository, keep the Ion checkout installed and launch its console command from the target repository:

```sh
cd /path/to/your/project
uv run --project /path/to/ion ion
```

Replace `/path/to/ion` with the location where you cloned Ion. The target repository remains the current working directory and becomes Ion’s workspace.

Enter a specific task, for example:

> In `src/parser.py`, fix the reported off-by-one error. Add a regression test, run the focused test, and summarize the diff.

Use `/help` in the interface to see commands. Common commands include `/models`, `/connect`, `/doctor`, `/sessions`, `/resume TASK_ID`, and `/logs`. Press Enter to send a task; use Shift+Enter for a newline. `/doctor` checks the selected profile and, when credentials are available, its live provider and model capabilities.

## Providers and configuration

Profiles live in [ion.toml](ion.toml). The checked-in examples use these credential variables:

| Profiles | Environment variable |
| --- | --- |
| `openrouter-coding-free`, `openrouter-qwen-free`, `openrouter-free-router` | `OPENROUTER_API_KEY` |
| `groq-qwen-dev` | `GROQ_API_KEY` |
| `deepseek-direct` | `DEEPSEEK_API_KEY` |
| `qwen-direct` | `DASHSCOPE_API_KEY` |

Provider catalogs, model availability, and free-tier quotas can change. Check the current profile with `/doctor`; a profile name does not guarantee that a provider will offer a model or free quota at all times.

To use a separate configuration file, set `ION_CONFIG=/path/to/ion.toml`. By default, Ion loads `.env` beside the active configuration file; set `ION_ENV_FILE` to use another environment file. See [interfaces and data](docs/interfaces-and-data.md) for configuration fields.

## Development

```sh
make setup
make test
```

`make test` runs the offline test suite. See the [agile delivery guide](docs/agile.md) for contribution expectations and validation practices.

## Help and documentation

- [Documentation index](docs/README.md)
- [Architecture](docs/architecture.md)
- [Execution and tools](docs/execution-and-tools.md)
- [Task lifecycle, recovery, and verification](docs/task-lifecycle-and-verification.md)
- [Context management](docs/context-management.md)
- [Security and trust boundaries](docs/security.md)
- [Open an issue](https://github.com/Trishix/ion/issues)

## Maintainers and contributions

Ion is maintained in the [Trishix/ion repository](https://github.com/Trishix/ion). Bug reports, focused fixes, and documentation improvements are welcome through issues and pull requests. Keep changes reviewable, add a focused regression test for behavior changes, and update the relevant reference documentation; the [agile delivery guide](docs/agile.md) has the project workflow.

## Data and safety

Ion sends the task and selected repository context to the configured model provider. Session records, diagnostics, and artifacts are stored locally under `$ION_DATA_DIR`, or by default under `~/.local/share/ion` (respecting `XDG_DATA_HOME`). Local data is not encrypted at rest in this version. Commands run with the local user’s privileges, so use Ion with repositories and commands you trust. See [Security](docs/security.md) for the limits of the current protections.
