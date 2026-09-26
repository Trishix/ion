from __future__ import annotations

import asyncio
import os
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Static, TextArea

from ion.artifacts import ArtifactStore
from ion.config import AppConfig, resolve_credential, resolve_profile, validate_task
from ion.contracts import ModelInfo, ModelProfile
from ion.doctor import Doctor
from ion.engine import Engine
from ion.model_selection import select_model
from ion.models.catalog import ModelCatalog
from ion.processes import CommandSupervisor
from ion.providers.openai_compatible import OpenAICompatibleProvider
from ion.storage import RunStore
from ion.tools.registry import ToolDispatcher
from ion.workspace import Workspace


class IonApp(App):
    CSS = """
    Vertical { padding: 0 2; }
    TextArea { height: 5; border: solid $accent; }
    #actions { height: 3; padding: 0; }
    #activity { height: 1fr; min-height: 4; border: solid $surface-lighten-2; }
    #status { margin: 1 0; }
    #models { height: 11; display: none; }
    Button { margin: 0 1 0 0; }
    """
    BINDINGS = [("ctrl+q", "quit", "Quit")]

    def __init__(self, config: AppConfig, repo_hint: str = "") -> None:
        super().__init__()
        self.config = config
        self.repo_hint = repo_hint
        self.mode = "evaluation" if config.evaluation_profile else "product"
        self.profile_name = config.evaluation_profile or config.default_profile
        self.profile_override: ModelProfile | None = None
        self.options: dict[str, tuple[str, ModelInfo]] = {}
        self.engine: Engine | None = None
        self.running_task: asyncio.Task | None = None
        self.active_task_id: str | None = None
        self.store: RunStore | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("Ion — local coding harness")
            yield Static("", id="profile")
            yield Input(value=self.repo_hint, placeholder="Target repository path", id="repo")
            yield TextArea(id="task")
            yield Input(placeholder="/models, /doctor, /history, /inspect ID, or /steer TEXT", id="command")
            with Horizontal(id="actions"):
                yield Button("Run task", id="run", variant="primary")
                yield Button("Cancel", id="cancel")
            yield Static("Confirm the target path and enter a task.", id="status")
            with VerticalScroll(id="activity"):
                yield Static("Activity and results appear here.", id="log")
            with VerticalScroll(id="models"):
                yield Static("", id="model_content")
        yield Footer()

    def on_mount(self) -> None:
        self.store = RunStore(self._data_root() / "runs.sqlite3")
        self.query_one("#cancel", Button).disabled = True
        self._profile_label()

    def on_unmount(self) -> None:
        if self.store:
            if self.active_task_id:
                self.store.interrupt(self.active_task_id)
            self.store.close()

    @staticmethod
    def _data_root() -> Path:
        return Path(os.environ.get("ION_DATA_DIR", Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "ion"))

    def _profile_label(self) -> None:
        profile = self.profile_override or resolve_profile(self.config, self.profile_name, self.mode)
        _, key_name = resolve_credential(profile, self.mode)
        key = "available" if resolve_credential(profile, self.mode)[0] else "missing"
        self.query_one("#profile", Static).update(f"Profile: {self.profile_name} · Model: {profile.model_id} · {key_name}: {key}")

    def _status(self, value: str) -> None:
        self.query_one("#status", Static).update(value)

    def _log(self, value: str) -> None:
        widget = self.query_one("#log", Static)
        current = str(widget.render())
        widget.update((current + "\n" + value)[-16000:])

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "command":
            return
        command = event.value.strip()
        event.input.value = ""
        if command == "/models":
            self.run_worker(self.show_models(), exclusive=True)
        elif command == "/doctor":
            checks = Doctor().run(self.config, self.profile_name, self.mode)
            self._log("\n".join(f"{item.status}: {item.name} — {item.detail}" for item in checks))
        elif command == "/history":
            assert self.store
            rows = self.store.recent()
            self._log("\n".join(f"{row['created_at']} · {row['status']} · {row['task']['text'][:100]} · {row['task_id']}" for row in rows) if rows else "No saved tasks yet.")
        elif command.startswith("/inspect "):
            assert self.store
            row = self.store.inspect(command.removeprefix("/inspect ").strip())
            if row is None:
                self._status("Task ID not found. Use /history to list saved runs.")
            else:
                result = row["result"]
                details = [
                    f"Task: {row['task_id']}", f"Status: {row['status']}",
                    f"Repository: {row['task']['repo_path']}", f"Request: {row['task']['text']}",
                ]
                if result:
                    details += [f"Result: {result['summary']}", f"Changed: {', '.join(result['changed_files']) or 'none'}", f"Verification records: {len(result['verification_ids'])}"]
                details += [f"{event['phase']}: {event['message']}" for event in row["events"][-20:]]
                self._log("\n".join(details))
        elif command.startswith("/steer "):
            if self.engine is None:
                self._status("No task is running. Enter a new task in the task field.")
            else:
                await self.engine.steer(command.removeprefix("/steer "))
                self._status("Steering queued for the next model turn.")
        else:
            self._status("Available commands: /models, /doctor, /history, /inspect ID, /steer TEXT")

    async def show_models(self) -> None:
        container = self.query_one("#models", VerticalScroll)
        container.display = True
        await container.remove_children()
        self.options.clear()
        if self.mode == "evaluation":
            profile = resolve_profile(self.config, self.profile_name, "evaluation")
            await container.mount(Static(f"Evaluation model locked: {profile.model_id} ({profile.provider})"))
            return
        await container.mount(Static("Choose a provider profile. Set its key in your terminal."))
        for index, name in enumerate(self.config.profiles):
            await container.mount(Button(f"Profile: {name}", id=f"profile-{index}"))
        profile = self.profile_override or resolve_profile(self.config, self.profile_name, self.mode)
        credential, key_name = resolve_credential(profile, self.mode)
        if not credential:
            await container.mount(Static(f"Set {key_name} to discover live models."))
            return
        self._status("Loading provider models…")
        result = await ModelCatalog(credential).list(profile)
        if result.status != "available":
            await container.mount(Static(f"Model catalog {result.status}. Configured model remains available."))
        for index, info in enumerate(result.entries):
            if not info.available:
                continue
            option_id = f"model-{index}"
            self.options[option_id] = (self.profile_name, info)
            eligible = info.text_only and info.context_window
            price = "free" if info.free is True else "paid" if info.free is False else "price unknown"
            label = f"{info.model_id} · {price} · {'select' if eligible else 'limits unknown'}"
            await container.mount(Button(label, id=option_id, disabled=not bool(eligible)))
        self._status("Choose a listed model for the next task.")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "run":
            if self.running_task and not self.running_task.done():
                self._status("A task is already running.")
                return
            self.running_task = asyncio.create_task(self._run_task())
        elif button_id == "cancel":
            if not self.running_task or self.running_task.done():
                self._status("No task is running.")
                return
            if self.engine:
                await self.engine.cancel()
            if self.running_task and not self.running_task.done():
                self.running_task.cancel()
            self._status("Cancelling current task; partial files are preserved.")
        elif button_id.startswith("profile-"):
            if self.running_task and not self.running_task.done():
                self._status("Wait for the current task before changing profiles.")
                return
            self.profile_name = list(self.config.profiles)[int(button_id.split("-")[1])]
            self.profile_override = None
            self._profile_label()
            self.run_worker(self.show_models(), exclusive=True)
        elif button_id in self.options:
            if self.running_task and not self.running_task.done():
                self._status("Wait for the current task before changing models.")
                return
            name, info = self.options[button_id]
            profile = resolve_profile(self.config, name, self.mode)
            if info.max_output_tokens is None:
                info = info.model_copy(update={"max_output_tokens": profile.max_output_tokens})
            try:
                self.profile_override = select_model(profile, info, self.mode)
            except ValueError as exc:
                self._status(str(exc))
                return
            self._profile_label()
            self._status(f"Selected {info.model_id} for the next task.")

    async def _run_task(self) -> None:
        profile = self.profile_override or resolve_profile(self.config, self.profile_name, self.mode)
        credential, key_name = resolve_credential(profile, self.mode)
        if not credential:
            self._status(f"Set {key_name} in this terminal before starting a live task.")
            return
        try:
            path = Path(self.query_one("#repo", Input).value).expanduser().resolve(strict=True)
            text = self.query_one("#task", TextArea).text
            task = validate_task({"text": text, "repo_path": str(path), "profile_name": self.profile_name, "mode": self.mode})
            workspace = Workspace.capture(path)
            data_root = self._data_root()
            artifacts = ArtifactStore(data_root / "artifacts" / task.task_id)
            supervisor = CommandSupervisor(workspace, artifacts, credential)
            dispatcher = ToolDispatcher(workspace, artifacts, supervisor)
            self.engine = Engine(self.config, OpenAICompatibleProvider(profile, credential), dispatcher, profile_override=profile)
            assert self.store
            self.store.begin(task)
            self.active_task_id = task.task_id
            self.query_one("#run", Button).disabled = True
            self.query_one("#cancel", Button).disabled = False
            self._status("Running task…")
            consumer = asyncio.create_task(self._consume_events())
            try:
                result = await self.engine.run(task)
                await consumer
                self.store.finish(result)
                self.active_task_id = None
            finally:
                if not consumer.done():
                    consumer.cancel()
            self._log(f"Result: {result.outcome.value}\n{result.summary}\nChanged: {', '.join(result.changed_files) or 'none'}\nVerification records: {len(result.verification_ids)}")
            if result.patch_artifact_id:
                self._log("Patch:\n" + artifacts.read(result.patch_artifact_id).decode("utf-8", "replace")[:12000])
            self._status(f"{result.outcome.value}: {result.summary[:160]}")
        except asyncio.CancelledError:
            self._status("Task cancelled. Partial repository changes remain.")
        except Exception as exc:
            self._status(f"Cannot run task: {type(exc).__name__}: {exc}")
        finally:
            if self.active_task_id and self.store:
                self.store.interrupt(self.active_task_id)
                self.active_task_id = None
            self.engine = None
            self.query_one("#run", Button).disabled = False
            self.query_one("#cancel", Button).disabled = True

    async def _consume_events(self) -> None:
        assert self.engine
        async for event in self.engine.events():
            if self.store and self.active_task_id:
                self.store.append(self.active_task_id, event)
            self._log(f"{event.phase.value}: {event.message}")
