from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from ion.contracts import ModelEvent, ModelProfile, ModelRequest


class OpenAICompatibleProvider:
    def __init__(
        self,
        profile: ModelProfile,
        credential: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.profile = profile
        self.credential = credential
        self.transport = transport

    async def generate(self, request: ModelRequest) -> AsyncIterator[ModelEvent]:
        body: dict = {
            "model": self.profile.model_id,
            "messages": list(request.messages),
            "max_tokens": request.max_output_tokens,
            "stream": False,
        }
        if self.profile.tool_protocol == "native" and request.tools:
            body["tools"] = list(request.tools)
            body["tool_choice"] = "auto"
        try:
            async with httpx.AsyncClient(
                base_url=self.profile.endpoint.rstrip("/") + "/",
                transport=self.transport,
                follow_redirects=False,
                timeout=60,
            ) as client:
                response = await client.post(
                    "chat/completions",
                    headers={"Authorization": f"Bearer {self.credential}"},
                    json=body,
                )
            if response.status_code in (401, 403):
                yield ModelEvent(kind="error", error="provider authentication failed")
                return
            if response.status_code == 429:
                yield ModelEvent(kind="error", error="provider rate limit")
                return
            response.raise_for_status()
            payload = response.json()
            choice = payload["choices"][0]
            message = choice["message"]
            content = message.get("content")
            if isinstance(content, str) and content:
                yield ModelEvent(kind="text_delta", text=content)
            for call in message.get("tool_calls") or []:
                function = call["function"]
                arguments = json.loads(function["arguments"])
                if not isinstance(arguments, dict):
                    raise ValueError("tool arguments must be an object")
                yield ModelEvent(kind="tool_call", tool=function["name"], arguments=arguments, call_id=call["id"])
            usage = payload.get("usage")
            if isinstance(usage, dict):
                yield ModelEvent(kind="usage", usage={key: value for key, value in usage.items() if isinstance(value, int)})
            yield ModelEvent(kind="completed")
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            # Provider bodies can contain credentials; never retain raw response text.
            category = "provider request failed" if isinstance(exc, httpx.HTTPError) else "malformed provider response"
            yield ModelEvent(kind="error", error=category)
