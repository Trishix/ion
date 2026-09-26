from ion.memory.store import MemoryStore


def test_memory_observations_are_scoped_searchable_and_source_linked(tmp_path):
    store = MemoryStore(tmp_path / "knowledge.sqlite3")
    observed = store.observe({
        "scope": "repo:demo",
        "fact_key": "test.command",
        "text": "Run python -m pytest tests",
        "evidence_kind": "observed",
        "source_refs": ["README.md:abc"],
        "supporting_hashes": ["abc"],
    })
    assert observed.status == "active"
    assert [item.memory_id for item in store.query("repo:demo", "pytest")] == [observed.memory_id]
    assert store.query("repo:other", "pytest") == []
    store.close()


def test_invalidation_and_forgetting_remove_facts_from_active_retrieval(tmp_path):
    store = MemoryStore(tmp_path / "knowledge.sqlite3")
    first = store.observe({"scope": "repo", "fact_key": "entry", "text": "src/app.py", "evidence_kind": "observed", "source_refs": ["app.py:one"]})
    derived = store.observe({"scope": "repo", "fact_key": "recipe", "text": "Run the app tests", "evidence_kind": "derived", "source_refs": ["app.py:one"], "supporting_hashes": ["one"]})
    assert store.invalidate("app.py:one") >= 2
    assert store.query("repo", "app") == []
    replacement = store.observe({"scope": "repo", "fact_key": "entry", "text": "src/main.py", "evidence_kind": "observed", "source_refs": ["main.py:two"]})
    store.forget(replacement.memory_id)
    assert store.query("repo", "main") == []
    store.close()


def test_same_fact_records_retain_history_and_explicit_replacement(tmp_path):
    store = MemoryStore(tmp_path / "knowledge.sqlite3")
    old = store.observe({"scope": "repo", "fact_key": "test.command", "text": "pytest", "evidence_kind": "observed", "source_refs": ["pyproject.toml:a"]})
    new = store.observe({"scope": "repo", "fact_key": "test.command", "text": "pytest -q", "evidence_kind": "observed", "source_refs": ["pyproject.toml:b"], "supersedes_id": old.memory_id})
    assert store.get(old.memory_id).status == "superseded"
    assert store.get(new.memory_id).status == "active"
    store.close()
