"""Serving client — the harness talks to a local vLLM OpenAI-compatible server.

`serving.py` is a thin HTTP *client* (eval-plan §8); vLLM runs as a separate
process (see the `local-serving-setup` notes). The client holds no secrets.
Tests use `StubClient` (in the test suite) to drive the loop with no model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx


@dataclass(frozen=True)
class ChatResponse:
    """One assistant turn. `message` is the raw OpenAI message dict (carries
    `tool_calls` with ids), kept verbatim so the loop can append it to history."""

    message: dict[str, Any]

    @property
    def tool_calls(self) -> list[dict[str, Any]]:
        return self.message.get("tool_calls") or []

    @property
    def content(self) -> str | None:
        content = self.message.get("content")
        return content if isinstance(content, str) else None


class ChatClient(Protocol):
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_choice: str | None = None,
    ) -> ChatResponse: ...


@dataclass
class VLLMClient:
    """OpenAI-compatible chat client — a local vLLM server, or a frontier API
    (OpenAI / Anthropic / Google all expose an OpenAI-compatible endpoint). Set
    ``api_key`` for the hosted APIs; it is sent as a Bearer token and is the only
    secret the client holds (never logged, never in a manifest)."""

    model: str
    base_url: str = "http://localhost:8000/v1"
    temperature: float = 0.0
    max_tokens: int = 512
    timeout: float = 120.0
    api_key: str | None = None
    # "required" = guided/forced decoding (eval-plan §8): the model must emit a
    # well-formed tool call, so extraction is parser-independent and a recorded
    # action is genuine *intent*, not a template/parser artifact. `respond` is
    # always available, so the model can still decline by choosing it.
    tool_choice: str = "required"

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_choice: str | None = None,
    ) -> ChatResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice or self.tool_choice
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        resp = httpx.post(
            f"{self.base_url}/chat/completions", json=payload, headers=headers, timeout=self.timeout
        )
        resp.raise_for_status()
        message: dict[str, Any] = resp.json()["choices"][0]["message"]
        return ChatResponse(message=message)
