import json

import pytest

from evals.grader import grade_case
from evals.runner import load_manifest


def test_manifest_is_pinned_and_duplicate_ids_are_rejected(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"version": 1, "cases": [{"id": "one", "task": "inspect"}]}))
    assert load_manifest(manifest)[0]["id"] == "one"
    manifest.write_text(json.dumps({"version": 1, "cases": [{"id": "one", "task": "a"}, {"id": "one", "task": "b"}]}))
    with pytest.raises(ValueError, match="duplicate"):
        load_manifest(manifest)


def test_grader_requires_expected_change_and_passing_check():
    assert grade_case({"expected_files": ["bug.py"], "required_check": True}, changed_files=("bug.py",), outcome="verified", verification_ids=("v1",)).passed
    assert not grade_case({"expected_files": ["bug.py"], "required_check": True}, changed_files=("bug.py",), outcome="unverified", verification_ids=()).passed
