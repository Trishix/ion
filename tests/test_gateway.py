import json
from pathlib import Path

import httpx
import pytest

from ion.config import load_config, resolve_profile
from ion.contracts import ModelRequest
from ion.providers.openai_compatible import OpenAICompatibleProvider


@pytest.mark.asyncio
async def test_openai_compatible_chat_sends_text_and_decodes_tool_call():
    profile = resolve_profile(load_config(Path(__file__).resolve().parents[1] / "ion.toml"), "groq-qwen-dev", "product")

    def handle(request):
        assert request.url.path == "/openai/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer fixture-key"
        body = json.loads(request.content)
        assert body["model"] == profile.model_id
        assert body["messages"] == [{"role": "user", "content": "Read a file"}]
        assert body["tools"][0]["function"]["name"] == "file_read"
        return httpx.Response(200, json={"choices": [{"message": {"content": None, "tool_calls": [{"id": "c1", "function": {"name": "file_read", "arguments": '{"relative_path":"a.py"}'}}]}}]})

    request = ModelRequest(messages=({"role": "user", "content": "Read a file"},), tools=({"type": "function", "function": {"name": "file_read"}},), max_output_tokens=200, profile_digest="fixture")
    events = [item async for item in OpenAICompatibleProvider(profile, "fixture-key", httpx.MockTransport(handle)).generate(request)]
    assert [item.kind for item in events] == ["tool_call", "completed"]
    assert events[0].arguments == {"relative_path": "a.py"}


@pytest.mark.asyncio
async def test_provider_auth_error_hides_response_body():
    profile = resolve_profile(load_config(Path(__file__).resolve().parents[1] / "ion.toml"), "deepseek-direct", "product")
    transport = httpx.MockTransport(lambda _: httpx.Response(401, text="fixture-key rejected"))
    request = ModelRequest(messages=({"role": "user", "content": "Hello"},), max_output_tokens=100, profile_digest="fixture")
    events = [item async for item in OpenAICompatibleProvider(profile, "fixture-key", transport).generate(request)]
    assert events[0].kind == "error"
    assert "fixture-key" not in events[0].error
