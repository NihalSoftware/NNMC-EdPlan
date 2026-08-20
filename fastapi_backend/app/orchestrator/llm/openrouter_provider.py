from __future__ import annotations

from typing import Any

import httpx

from app.orchestrator.llm.base_provider import BaseLLMProvider, LLMProviderError, StructuredOutput
from app.orchestrator.llm.llm_models import (
    LLMHealthCheck,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMUsage,
)
from app.orchestrator.llm.model_config import LLMModelConfig


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter-compatible provider using the shared LLM abstraction."""

    provider_name = "openrouter"

    def __init__(self, model_config: LLMModelConfig | None = None) -> None:
        self.model_config = model_config or LLMModelConfig.from_env()

    async def generate(self, request: LLMRequest) -> LLMResponse:
        payload = self.build_request_payload(request)
        headers = self.build_headers()
        async with httpx.AsyncClient(timeout=self.model_config.timeout) as client:
            try:
                response = await client.post(
                    f"{self.model_config.api_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise LLMProviderError(
                    "OpenRouter request failed.",
                    metadata={"provider": self.provider_name, "error": str(exc)},
                ) from exc
        return self.parse_response(response.json())

    async def generate_structured(
        self,
        request: LLMRequest,
        response_model: type[StructuredOutput],
    ) -> StructuredOutput:
        response = await self.generate(request)
        try:
            return response_model.model_validate_json(response.content)
        except ValueError as exc:
            raise LLMProviderError(
                "OpenRouter response could not be parsed as structured output.",
                metadata={"provider": self.provider_name, "model": response.model},
            ) from exc

    async def health_check(self) -> LLMHealthCheck:
        if self.model_config.api_key is None:
            return LLMHealthCheck(
                provider=self.provider_name,
                ok=False,
                message="OPENROUTER_API_KEY is not configured.",
                metadata={
                    "network_enabled": False,
                    "model": self.model_config.primary_model,
                    "base_url": self.model_config.api_base_url,
                },
            )
        return LLMHealthCheck(
            provider=self.provider_name,
            ok=True,
            message="OpenRouter provider is configured.",
            metadata={
                "network_enabled": True,
                "model": self.model_config.primary_model,
                "base_url": self.model_config.api_base_url,
            },
        )

    def build_headers(self) -> dict[str, str]:
        if self.model_config.api_key is None:
            raise LLMProviderError(
                "OPENROUTER_API_KEY is required for OpenRouter requests.",
                metadata={"provider": self.provider_name},
            )
        return {
            "Authorization": f"Bearer {self.model_config.api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }

    def build_request_payload(self, request: LLMRequest) -> dict[str, Any]:
        messages = [message.model_dump(mode="json") for message in request.messages]
        if request.system_prompt:
            messages = [
                {"role": "system", "content": request.system_prompt, "metadata": {}}
            ] + messages

        payload: dict[str, Any] = {
            "model": request.model or self.model_config.primary_model,
            "messages": messages,
            "temperature": (
                request.temperature
                if request.temperature is not None
                else self.model_config.temperature
            ),
            "max_tokens": (
                request.max_tokens
                if request.max_tokens is not None
                else self.model_config.max_tokens
            ),
            "metadata": request.metadata,
        }
        if request.tools:
            payload["tools"] = request.tools
            payload["tool_choice"] = request.tool_choice or "auto"
        return payload

    @staticmethod
    def parse_response(raw_response: dict[str, Any]) -> LLMResponse:
        choices = raw_response.get("choices") or []
        first_choice = choices[0] if choices else {}
        message = first_choice.get("message") or {}
        usage = raw_response.get("usage")
        tool_calls = []
        for item in message.get("tool_calls") or []:
            function = item.get("function") or {}
            arguments = function.get("arguments") or {}
            if isinstance(arguments, str):
                try:
                    import json

                    arguments = json.loads(arguments)
                except ValueError:
                    arguments = {}
            tool_calls.append(
                LLMToolCall(
                    id=item.get("id"),
                    name=str(function.get("name", "")),
                    arguments=arguments if isinstance(arguments, dict) else {},
                )
            )

        return LLMResponse(
            model=str(raw_response.get("model", "")),
            content=str(message.get("content", "")),
            metadata=dict(raw_response.get("metadata") or {}),
            usage=LLMUsage.model_validate(usage) if usage is not None else None,
            finish_reason=first_choice.get("finish_reason"),
            tool_calls=tool_calls,
            raw_response=raw_response,
        )
