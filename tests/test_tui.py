from pathlib import Path

import pytest
from textual.widgets import Button, Input, OptionList, RichLog, Static

from ion.config import load_config
from ion.contracts import ModelEvent
from ion.providers.scripted import ScriptedProvider
from ion.tui.app import IonApp
from ion.tui.widgets import Brand, Composer, EntryDialog, Picker


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv('ION_DATA_DIR', str(tmp_path / 'ion-data'))
    for name in ('GROQ_API_KEY', 'OPENROUTER_API_KEY', 'AI_API_KEY', 'DEEPSEEK_API_KEY', 'DASHSCOPE_API_KEY'):
        monkeypatch.delenv(name, raising=False)
    return IonApp(load_config(Path(__file__).resolve().parents[1] / 'ion.toml'), str(tmp_path))


@pytest.mark.asyncio
@pytest.mark.parametrize('size', [(120, 40), (80, 24)])
async def test_home_composer_and_searchable_model_dialog(app, size):
    async with app.run_test(size=size) as pilot:
        assert app.query_one(Brand).render().plain.strip()
        composer = app.query_one(Composer)
        assert composer.has_focus
        assert composer.region.bottom <= size[1]
        assert not app.query_one('#cancel', Button).display
        await app.show_models()
        await pilot.pause()
        assert isinstance(app.screen, Picker)
        assert app.screen.query_one(OptionList).option_count == len(app.config.profiles)
        app.screen.query_one(Input).value = 'groq'
        await pilot.pause()
        await pilot.press('enter')
        await pilot.pause()
        assert app.profile_name == 'groq-qwen-dev'
        assert not isinstance(app.screen, Picker)


@pytest.mark.asyncio
async def test_commands_repo_and_session_only_masked_connection(app, monkeypatch, tmp_path):
    async with app.run_test() as pilot:
        await pilot.press('ctrl+p')
        assert isinstance(app.screen, Picker)
        await pilot.press('escape')
        original_repo = app.repo_path
        await app._command('/repo')
        await pilot.pause()
        assert app.repo_path == original_repo
        assert 'locked' in str(app.query_one('#status', Static).render()).lower()
        await app._command('/connect')
        await pilot.pause()
        app.screen.query_one(Input).value = 'openrouter'
        await pilot.pause()
        await pilot.press('enter')
        await pilot.pause()
        assert app.screen.query_one(Input).password
        monkeypatch.setenv('OPENROUTER_API_KEY', '')
        app.screen.query_one(Input).value = 'fixture-session-key'
        await pilot.press('enter')
        await pilot.pause()
        import os
        assert os.environ['OPENROUTER_API_KEY'] == 'fixture-session-key'
        assert not (tmp_path / '.env').exists()


@pytest.mark.asyncio
async def test_enter_runs_engine_and_new_returns_to_home(app, monkeypatch, tmp_path):
    (tmp_path / 'readme.txt').write_text('Hello\n')
    provider = ScriptedProvider([
        [ModelEvent(kind='tool_call', tool='file_read', arguments={'relative_path': 'readme.txt'}, call_id='r'), ModelEvent(kind='completed')],
        [ModelEvent(kind='tool_call', tool='finish_request', arguments={'summary': 'Read the file'}, call_id='f'), ModelEvent(kind='completed')],
    ])
    monkeypatch.setenv('OPENROUTER_API_KEY', 'fixture-key')
    monkeypatch.setattr('ion.tui.app.OpenAICompatibleProvider', lambda *args: provider)
    async with app.run_test(size=(120, 40)) as pilot:
        app.query_one(Composer).text = 'Read readme.txt'
        await pilot.press('enter')
        await pilot.pause()
        assert app.running_task is not None
        await app.running_task
        assert app.screen.has_class('session')
        assert app.query_one('#activity', RichLog).lines
        assert 'Read the file' in str(app.query_one('#status', Static).render())
        assert app.query_one('#sidebar').display
        await pilot.resize_terminal(80, 24)
        await pilot.pause()
        assert not app.query_one('#sidebar').display
        log = app.query_one(RichLog)
        assert log.virtual_size.width <= log.scrollable_content_region.width
        await pilot.press('ctrl+n')
        assert not app.screen.has_class('session')
        assert app.query_one(Composer).has_focus


@pytest.mark.asyncio
async def test_leader_model_shortcut_does_not_type_into_prompt(app):
    async with app.run_test() as pilot:
        await pilot.press('ctrl+x', 'm')
        await pilot.pause()
        assert isinstance(app.screen, Picker)


@pytest.mark.asyncio
async def test_singular_model_command_opens_picker(app):
    async with app.run_test() as pilot:
        app.query_one(Composer).text = '/model'
        await pilot.press('enter')
        await pilot.pause()
        assert isinstance(app.screen, Picker)


@pytest.mark.asyncio
async def test_logs_command_shows_diagnostic_location(app):
    async with app.run_test() as pilot:
        await app._command('/logs')
        await pilot.pause()
        assert app.screen.has_class('session')
        assert 'Harness diagnostics' in str(app.query_one('#session-header', Static).render())
        assert app.query_one('#activity', RichLog).lines
