import os
from pathlib import Path

from ion.launcher import load_local_env


def test_local_dotenv_is_product_only_and_does_not_override_process_environment(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("GROQ_API_KEY=dotenv-value\nOPENROUTER_API_KEY=openrouter-value\n")
    monkeypatch.delenv("ION_ENV_FILE", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "shell-value")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    try:
        load_local_env(tmp_path / "ion.toml", evaluation=False)
        assert os.environ["GROQ_API_KEY"] == "shell-value"
        assert os.environ["OPENROUTER_API_KEY"] == "openrouter-value"
    finally:
        os.environ.pop("OPENROUTER_API_KEY", None)


def test_locked_evaluation_does_not_load_local_dotenv(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("AI_API_KEY=local-value\n")
    monkeypatch.delenv("AI_API_KEY", raising=False)
    load_local_env(tmp_path / "ion.toml", evaluation=True)
    assert "AI_API_KEY" not in os.environ
