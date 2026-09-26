# Ion

Ion is a terminal coding harness for the AI Harness Hackathon 2026. It reads a text task, inspects a local repository, applies guarded edits, runs bounded commands, and reports changed files and verification evidence.

## Start

Requires a terminal and Python 3.12 or newer. From this repository:

```sh
make setup
export GROQ_API_KEY="<your key>"
make run
```

The default profile is Groq Qwen. Enter the target repository path and task in the TUI, then select **Run task**. `ION_REPO=/path/to/repo make run` prefills the path. `/doctor` shows local configuration and credential status. `/models` lists profiles and, when a key is available, discovers selectable provider models. `/history` shows saved runs. `make test` runs the offline suite. `make clean` removes disposable build and test caches.

## Choose a provider

The committed [ion.toml](ion.toml) contains Groq Qwen, OpenRouter Qwen and DeepSeek free model profiles, plus direct DeepSeek and Qwen API examples. Export the matching key:

| Profile | Credential |
| --- | --- |
| `groq-qwen-dev` | `GROQ_API_KEY` |
| `openrouter-qwen-free`, `openrouter-deepseek-free` | `OPENROUTER_API_KEY` |
| `deepseek-direct` | `DEEPSEEK_API_KEY` |
| `qwen-direct` | `DASHSCOPE_API_KEY` |

The direct provider APIs may require a paid account. A `:free` OpenRouter model is subject to provider availability and rate limits. Catalog availability is checked live; these profiles are examples, not a promise that every model remains free or available.

To connect another OpenAI compatible text model, create a TOML file outside the target repository with `schema_version = 1`, `default_profile`, and a `[profiles.NAME]` section. Specify `provider`, `base_url` (HTTPS), `model`, `api_key_env`, `protocol = "openai_chat"`, `tool_protocol = "native"` or `"structured_json"`, `text_only = true`, `locked = false`, `context_window`, and `max_output_tokens`. Launch with `ION_CONFIG=/path/to/your.toml make run`. A provider specific key is preferred; `AI_API_KEY` is the fallback in normal use. Never place key values in TOML or Git.

## Hackathon evaluation

The Makefile exposes `make setup`, `make run`, `make test`, and `make clean`. The evaluator can export `AI_API_KEY` before launch. Once the committee gives the exact provider, model, and endpoint, add a profile with `locked = true` and set `evaluation_profile = "NAME"` in `ion.toml`. That mode reads **only** `AI_API_KEY` and disables model switching. The announcement reported Qwen and DeepSeek model families; the exact official model IDs and credential provider are still required to freeze an evaluation profile. The project does not claim official submission readiness until those are confirmed and a live end to end run succeeds.

Ion executes repository commands on the local machine. Use it on repositories you trust. Tool output, patches, and run history are retained under the user's Ion data directory. The current engine is foreground and its verification recognizes a narrow set of relevant pytest runs; durable resume and repository memory remain on the [implementation plan](docs/implementation-plan.md).

See [the product documentation](docs/README.md), [hackathon rules](docs/rules.md), and [architecture](docs/architecture.md).
