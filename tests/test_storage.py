from ion.contracts import EngineEvent, Outcome, Phase, TaskResult, TaskSpec
from ion.storage import RunStore


def test_run_history_survives_reopen_and_records_interruption(tmp_path):
    path = tmp_path / "data" / "runs.sqlite3"
    task = TaskSpec(text="Fix the parser", repo_path=str(tmp_path), profile_name="groq-qwen-dev")
    store = RunStore(path)
    assert path.stat().st_mode & 0o077 == 0
    store.begin(task)
    store.append(task.task_id, EngineEvent(phase=Phase.inspect, message="Read parser.py"))
    store.finish(TaskResult(task_id=task.task_id, outcome=Outcome.unverified, summary="Needs broader checks"))
    store.close()

    reopened = RunStore(path)
    rows = reopened.recent()
    assert len(rows) == 1
    assert rows[0]["task"]["text"] == "Fix the parser"
    assert rows[0]["result"]["summary"] == "Needs broader checks"
    assert rows[0]["status"] == "unverified"
    reopened.interrupt(task.task_id)
    assert reopened.recent()[0]["status"] == "unverified"
    reopened.close()
