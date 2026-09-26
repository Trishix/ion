from pathlib import Path

import pytest

from ion.config import load_config, resolve_credential, resolve_profile


def test_profiles_use_provider_keys_and_evaluation_uses_ai_api_key(monkeypatch):
    config = load_config(Path(__file__).resolve().parents[1] / "ion.toml")
    profile = resolve_profile(config, "groq-qwen-dev", "product")
    monkeypatch.setenv("GROQ_API_KEY", "groq-only-test-value")
    monkeypatch.setenv("AI_API_KEY", "evaluation-test-value")
    assert resolve_credential(profile, "product") == ("groq-only-test-value", "GROQ_API_KEY")
    assert resolve_credential(profile, "evaluation") == ("evaluation-test-value", "AI_API_KEY")


def test_config_rejects_embedded_credential(tmp_path):
    path = tmp_path / "ion.toml"
    path.write_text('schema_version=1\ndefault_profile="x"\n[profiles.x]\nprovider="groq"\nbase_url="https://api.example/v1"\nmodel="x"\napi_key="secret"\ncontext_window=8192\nmax_output_tokens=1024\n')
    with pytest.raises(ValueError):
        load_config(path)
