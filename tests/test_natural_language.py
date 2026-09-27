from pathlib import Path
import json

import pytest

from ion.artifacts import ArtifactStore
from ion.config import load_config, resolve_profile
from ion.contracts import ModelEvent, TaskSpec
from ion.engine import Engine
from ion.processes import CommandSupervisor
from ion.providers.scripted import ScriptedProvider
from ion.tools.registry import ToolDispatcher
from ion.workspace import Workspace


def harness(tmp_path, turns, mode='product'):
    config = load_config(Path(__file__).resolve().parents[1] / 'ion.toml')
    config = config.model_copy(update={"economy": config.economy.model_copy(update={"enabled": True})})
    workspace = Workspace.capture(tmp_path)
    artifacts = ArtifactStore(tmp_path.parent / (tmp_path.name + '-artifacts'))
    dispatcher = ToolDispatcher(workspace, artifacts, CommandSupervisor(workspace, artifacts))
    provider = ScriptedProvider(turns)
    profile = resolve_profile(config, 'groq-qwen-dev', 'product').model_copy(update={'locked': mode == 'evaluation'})
    return Engine(config, provider, dispatcher, profile_override=profile), provider


@pytest.mark.asyncio
@pytest.mark.parametrize('mode', ['product', 'evaluation'])
@pytest.mark.parametrize('prompt', ['how should I use this repo', 'How do I add a new command?', 'Can you explain how to add a new command?'])
async def test_repo_question_returns_grounded_plain_language_answer(tmp_path, mode, prompt):
    source = '# Usage\nRun make setup, then make run.\n'
    (tmp_path / 'README.md').write_text(source)
    answer = 'The README says to run `make setup`, then `make run` from this repository.'
    engine, provider = harness(tmp_path, [
        [ModelEvent(kind='tool_call', tool='file_read', arguments={'relative_path': 'README.md'}, call_id='r')],
        [ModelEvent(kind='text_delta', text=answer), ModelEvent(kind='completed')],
    ], mode)
    result = await engine.run(TaskSpec(text=prompt, repo_path=str(tmp_path), profile_name='fixture', mode=mode))
    assert result.summary == answer
    assert len(provider.requests) == 2
    assert not result.changed_files
    assert (tmp_path / 'README.md').read_text() == source
    offered = {item['function']['name'] for item in provider.requests[0].tools}
    assert not offered & {'edit_file', 'write_file', 'patch_apply', 'command_start'}


@pytest.mark.asyncio
@pytest.mark.parametrize('prompt', [
    'Improves that repos readme of using part',
    'Can you improve the README usage section?',
    'Make the README usage section clearer',
])
async def test_readme_improvement_gets_edit_instead_of_advice_only(tmp_path, prompt):
    (tmp_path / 'README.md').write_text('# Usage\nRun the app.\n')
    engine, provider = harness(tmp_path, [
        [ModelEvent(kind='tool_call', tool='finish_request', arguments={'summary': 'You should add setup steps.'}, call_id='f')],
        [ModelEvent(kind='tool_call', tool='edit_file', arguments={
            'plan': 'Clarify the usage instructions.', 'read_id': 'r1',
            'old_text': 'Run the app.', 'new_text': 'Run `make setup`, then `make run`.', 'done': True,
        }, call_id='e')],
    ])
    result = await engine.run(TaskSpec(text=prompt, repo_path=str(tmp_path), profile_name='fixture'))
    assert result.changed_files == ('README.md',)
    assert '`make setup`' in (tmp_path / 'README.md').read_text()
    assert len(provider.requests) == 2
    assert provider.requests[1].tool_choice == 'edit_file'


@pytest.mark.asyncio
@pytest.mark.parametrize('mode', ['product', 'evaluation'])
async def test_question_cannot_modify_files_even_if_model_requests_it(tmp_path, mode):
    (tmp_path / 'README.md').write_text('# Usage\nRun the app.\n')
    engine, provider = harness(tmp_path, [
        [ModelEvent(kind='tool_call', tool='file_read', arguments={'relative_path': 'README.md'}, call_id='r')],
        [ModelEvent(kind='tool_call', tool='edit_file', arguments={
            'plan': 'Rewrite instructions.', 'read_id': 'r1', 'old_text': 'Run the app.',
            'new_text': 'Changed without permission.', 'done': True,
        }, call_id='e')],
        [ModelEvent(kind='text_delta', text='The README says to run the app.')],
    ], mode)
    result = await engine.run(TaskSpec(text='how should I use this repo', repo_path=str(tmp_path), profile_name='fixture', mode=mode))
    assert not result.changed_files
    assert 'Changed without permission' not in (tmp_path / 'README.md').read_text()
    assert result.summary == 'The README says to run the app.'


@pytest.mark.asyncio
async def test_prompt_fit_error_is_not_reported_as_spent_budget(tmp_path):
    (tmp_path / 'AGENTS.md').write_text('Required instruction.\n' * 3000)
    engine, provider = harness(tmp_path, [])
    result = await engine.run(TaskSpec(text='how should I use this repo', repo_path=str(tmp_path), profile_name='fixture'))
    assert not provider.requests
    assert result.outcome == 'blocked'
    assert 'context' in result.summary


@pytest.mark.asyncio
async def test_native_answer_envelope_is_shown_as_readable_prose(tmp_path):
    (tmp_path / 'README.md').write_text('# Usage\nRun python app.py.\n')
    answer = 'Run `python app.py`.\nPass a name as an optional argument.'
    engine, provider = harness(tmp_path, [
        [ModelEvent(kind='tool_call', tool='file_read', arguments={'relative_path': 'README.md'}, call_id='r')],
        [ModelEvent(kind='text_delta', text=json.dumps({'content': answer, 'summary': 'Usage explained'}))],
    ])
    result = await engine.run(TaskSpec(text='how should I use this repo', repo_path=str(tmp_path), profile_name='fixture'))
    assert result.summary == answer
    assert not result.changed_files


@pytest.mark.asyncio
@pytest.mark.parametrize('verb', ['Solve', 'Resolve', 'Repair'])
@pytest.mark.parametrize('mode', ['product', 'evaluation'])
async def test_solution_requests_receive_edit_tools_after_reading(tmp_path, verb, mode):
    from ion.workspace import digest
    source = 'value = 1\n'
    (tmp_path / 'bug.py').write_text(source)
    engine, provider = harness(tmp_path, [
        [ModelEvent(kind='tool_call', tool='file_read', arguments={'relative_path': 'bug.py'}, call_id='read')],
        [ModelEvent(kind='tool_call', tool='patch_apply', arguments={'edits': [{
            'path': 'bug.py', 'expected_hash': digest(source.encode()), 'old_text': 'value = 1', 'new_text': 'value = 2',
        }]}, call_id='patch')],
        [ModelEvent(kind='tool_call', tool='finish_request', arguments={'summary': 'Corrected the value; tests unavailable.'}, call_id='finish')],
    ], mode)
    result = await engine.run(TaskSpec(text=f'{verb} the wrong return value', repo_path=str(tmp_path), profile_name='fixture', mode=mode))
    assert 'patch_apply' in {tool['function']['name'] for tool in provider.requests[1].tools}
    assert (tmp_path / 'bug.py').read_text() == 'value = 2\n'
    assert result.changed_files == ('bug.py',)
    assert result.outcome == 'unverified'


@pytest.mark.asyncio
@pytest.mark.parametrize('prompt,summary,expected', [
    ('Handle the repository problem', 'Blocker: no edit tool is available.', 'blocked'),
    ('Handle the repository problem', 'Inspected the README.', 'unverified'),
    ('Explain the service', 'Blocker: the service source is missing.', 'blocked'),
])
async def test_incomplete_task_is_not_verified_by_unchanged_files(tmp_path, prompt, summary, expected):
    (tmp_path / 'README.md').write_text('# Project\n')
    engine, provider = harness(tmp_path, [
        [ModelEvent(kind='tool_call', tool='file_read', arguments={'relative_path': 'README.md'}, call_id='read')],
        [ModelEvent(kind='tool_call', tool='finish_request', arguments={'summary': summary}, call_id='finish')],
    ])
    result = await engine.run(TaskSpec(text=prompt, repo_path=str(tmp_path), profile_name='fixture'))
    assert result.outcome == expected
    assert result.verification_ids == ()


@pytest.mark.parametrize('prompt', ['Read the parser and run its tests', 'Find the test command and execute it'])
def test_inspection_with_explicit_execution_keeps_command_authority(prompt):
    from ion.intent import task_intent
    assert task_intent(prompt) == 'task'


@pytest.mark.parametrize('prompt', ['Delete obsolete files', 'Deleting the files in sample_project'])
def test_file_deletion_is_an_edit_request(prompt):
    from ion.intent import task_intent
    assert task_intent(prompt) == 'edit'
