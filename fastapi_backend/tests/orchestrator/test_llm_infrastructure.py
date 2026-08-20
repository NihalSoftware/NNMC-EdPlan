from __future__ import annotations

import pytest

from app.orchestrator.llm import (
    BaseLLMProvider,
    LLMMessage,
    LLMModelConfig,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    OpenRouterProvider,
    PromptCategory,
    PromptManager,
    PromptRegistry,
    PromptTemplate,
)
from app.orchestrator.services.student_orchestrator import StudentOrchestrator


def test_base_provider_is_abstract():
    with pytest.raises(TypeError):
        BaseLLMProvider()  # type: ignore[abstract]


def test_model_configuration_is_centralized_and_configurable():
    config = LLMModelConfig(
        primary_model="provider/model-a",
        fallback_model="provider/model-b",
        temperature=0.4,
        max_tokens=2048,
        timeout=45.0,
    )

    assert config.primary_model == "provider/model-a"
    assert config.fallback_model == "provider/model-b"
    assert config.temperature == 0.4
    assert config.max_tokens == 2048
    assert config.timeout == 45.0


def test_model_configuration_defaults_to_openrouter_target_model():
    config = LLMModelConfig()

    assert config.primary_model == "qwen/qwen3-7b-plus"
    assert config.api_base_url == "https://openrouter.ai/api/v1"


def test_prompt_manager_renders_registered_prompt():
    registry = PromptRegistry(
        [
            PromptTemplate(
                name="test.prompt",
                category=PromptCategory.INTENT_ROUTING,
                template="Route: {query}",
                required_variables={"query"},
            )
        ]
    )

    rendered = PromptManager(registry).render("test.prompt", {"query": "Plan my courses"})

    assert rendered == "Route: Plan my courses"


def test_prompt_manager_validates_required_variables():
    manager = PromptManager(
        PromptRegistry(
            [
                PromptTemplate(
                    name="test.prompt",
                    category=PromptCategory.RESPONSE_GENERATION,
                    template="Respond to {query}",
                    required_variables={"query"},
                )
            ]
        )
    )

    with pytest.raises(ValueError, match="missing variables"):
        manager.render("test.prompt", {})


def test_prompt_registry_contains_future_categories():
    registry = PromptRegistry()

    assert registry.list_by_category(PromptCategory.INTENT_ROUTING)
    assert registry.list_by_category(PromptCategory.MEMORY_SUMMARIZATION)
    assert registry.list_by_category(PromptCategory.RESPONSE_GENERATION)
    assert registry.list_by_category(PromptCategory.ACADEMIC_PLANNING)
    assert registry.list_by_category(PromptCategory.SCHEDULING)
    assert registry.list_by_category(PromptCategory.CAREER_GUIDANCE)
    assert registry.list_by_category(PromptCategory.FINANCE_GUIDANCE)
    assert registry.list_by_category(PromptCategory.ACADEMIC_SUCCESS)
    assert registry.list_by_category(PromptCategory.COLLEGE_COMPARISON)


def test_llm_request_response_serialization():
    request = LLMRequest(
        model="provider/model",
        system_prompt="System",
        messages=[LLMMessage(role="user", content="Hello")],
        tool_choice="auto",
        tools=[{"type": "function", "function": {"name": "get_plan"}}],
        metadata={"purpose": "test"},
    )
    response = LLMResponse(
        model="provider/model",
        content="Hello back",
        finish_reason="stop",
        tool_calls=[LLMToolCall(name="get_plan", arguments={"plan_id": "plan-1"})],
        metadata={"stub": True},
    )

    assert request.model_dump(mode="json")["messages"][0]["role"] == "user"
    assert request.model_dump(mode="json")["tools"][0]["function"]["name"] == "get_plan"
    assert response.model_dump(mode="json")["finish_reason"] == "stop"
    assert response.model_dump(mode="json")["tool_calls"][0]["name"] == "get_plan"


def test_openrouter_provider_builds_request_payload_without_network():
    provider = OpenRouterProvider(LLMModelConfig(primary_model="configured/model"))
    request = LLMRequest(
        system_prompt="System",
        messages=[LLMMessage(role="user", content="Hello")],
    )

    payload = provider.build_request_payload(request)

    assert payload["model"] == "configured/model"
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["content"] == "Hello"


def test_openrouter_provider_builds_and_parses_tool_calls():
    provider = OpenRouterProvider(LLMModelConfig(primary_model="configured/model"))
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="Validate my plan")],
        tools=[{"type": "function", "function": {"name": "validate_plan"}}],
    )

    payload = provider.build_request_payload(request)
    response = provider.parse_response(
        {
            "model": "configured/model",
            "choices": [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "function": {
                                    "name": "validate_plan",
                                    "arguments": '{"plan_id":"plan-1"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
        }
    )

    assert payload["tool_choice"] == "auto"
    assert response.tool_calls[0].name == "validate_plan"
    assert response.tool_calls[0].arguments == {"plan_id": "plan-1"}


@pytest.mark.asyncio
async def test_openrouter_provider_requires_api_key_for_requests():
    provider = OpenRouterProvider(LLMModelConfig(primary_model="configured/model"))

    health = await provider.health_check()

    assert health.ok is False
    assert health.metadata["network_enabled"] is False
    with pytest.raises(LLMProviderError, match="OPENROUTER_API_KEY"):
        await provider.generate(LLMRequest(messages=[LLMMessage(role="user", content="Hello")]))


def test_student_orchestrator_accepts_llm_provider_without_using_it():
    provider = OpenRouterProvider()

    orchestrator = StudentOrchestrator(llm_provider=provider)

    assert orchestrator.llm_provider is provider
