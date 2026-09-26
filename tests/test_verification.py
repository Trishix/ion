from ion.verification import observe_pytest


def test_relevant_pytest_output_is_observed_but_echo_is_not():
    fingerprint = "workspace-hash"
    changed = ("bug.py",)
    assert observe_pytest("python -m pytest tests/test_bug.py -q", "1 passed in 0.01s", 0, "op", fingerprint, changed)
    assert observe_pytest("echo '1 passed' && pytest tests/test_bug.py", "1 passed in 0.01s", 0, "op", fingerprint, changed) is None
    assert observe_pytest("python -m pytest tests/test_unrelated.py -q", "1 passed in 0.01s", 0, "op", fingerprint, changed) is None
