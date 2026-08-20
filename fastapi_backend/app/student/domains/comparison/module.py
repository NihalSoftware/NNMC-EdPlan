from __future__ import annotations

import json
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestrator.llm import (
    BaseLLMProvider,
    LLMMessage,
    LLMRequest,
    LLMResponse,
    OpenRouterProvider,
)
from app.orchestrator.modules.base_module import BaseModule
from app.orchestrator.schemas.module_response import ModuleResponse
from app.orchestrator.schemas.student_context import StudentContext
from app.student.domains.comparison.tools.registry import COMPARISON_TOOLS

MODULE_NAME = "college_comparison"
MODULE_DESCRIPTION = (
    "Help students compare Northern New Mexico College academic programs using existing NNMC data."
)

COMPARISON_ADVISOR_PROMPT = (
    "You are Northern New Mexico College's Program Comparison Advisor. "
    "Compare only factual information from "
    "the current NNMC catalog and the exposed program comparison tools. Never invent "
    "tuition, placement rates, acceptance rates, rankings, salaries, scholarships, or "
    "institution scores. Compare NNMC programs, not institutions. Explain objective tradeoffs "
    "using available catalog facts such as programs, credits, required courses, "
    "websites, and career mappings. If requested information is unavailable, state that it "
    "is not available in the current NNMC catalog. Ask for additional filters or IDs when "
    "the request is too broad or ambiguous."
)

SUPPORTED_TOOL_NAMES = {
    "search_universities",
    "compare_universities",
    "search_programs",
    "compare_programs",
    "compare_career_paths",
}


def get_tools():
    return COMPARISON_TOOLS


class CollegeComparisonModule(BaseModule):
    """Orchestrator module adapter for college comparison tools."""

    name = MODULE_NAME
    description = MODULE_DESCRIPTION

    def __init__(
        self,
        db: AsyncSession | None = None,
        tools: list[Any] | None = None,
        llm_provider: BaseLLMProvider | None = None,
        max_tool_iterations: int = 6,
        max_total_tool_calls: int = 10,
        max_same_tool_calls: int = 3,
    ) -> None:
        self.db = db
        self.tools = {tool.name: tool for tool in tools or get_tools()}
        self.llm_provider = llm_provider or OpenRouterProvider()
        self.max_tool_iterations = max_tool_iterations
        self.max_total_tool_calls = max_total_tool_calls
        self.max_same_tool_calls = max_same_tool_calls

    async def execute(self, context: StudentContext, query: str) -> ModuleResponse:
        messages = self._initial_messages(context, query)
        observations: list[dict[str, Any]] = []
        final_response: LLMResponse | None = None
        tool_counts: dict[str, int] = {}
        stop_reason: str | None = None

        for _ in range(self.max_tool_iterations):
            llm_response = await self.llm_provider.generate(
                LLMRequest(
                    messages=messages,
                    system_prompt=COMPARISON_ADVISOR_PROMPT,
                    tools=self.tool_schemas,
                    tool_choice="auto",
                    metadata={"module": self.name},
                )
            )
            final_response = llm_response
            tool_calls = self._tool_calls_from_response(llm_response)
            if not tool_calls:
                break

            allowed_tool_calls = self._budgeted_tool_calls(tool_calls, tool_counts)
            if not allowed_tool_calls:
                stop_reason = "tool_budget_exhausted"
                break

            messages.append(
                LLMMessage(
                    role="assistant",
                    content=llm_response.content or "Requesting NNMC program comparison tools.",
                    metadata={
                        "tool_calls": [
                            {
                                "id": tool_call.get("id"),
                                "name": tool_call["name"],
                                "arguments": tool_call["arguments"],
                            }
                            for tool_call in allowed_tool_calls
                        ]
                    },
                )
            )
            for tool_call in allowed_tool_calls:
                tool_counts[tool_call["name"]] = tool_counts.get(tool_call["name"], 0) + 1
                observation = await self._execute_tool_call(tool_call)
                observations.append(observation)
                messages.append(
                    LLMMessage(
                        role="tool",
                        content=json.dumps(jsonable_encoder(observation)),
                        metadata={
                            "tool_call_id": tool_call.get("id"),
                            "tool_name": tool_call["name"],
                        },
                    )
                )
            if len(observations) >= self.max_total_tool_calls:
                stop_reason = "max_total_tool_calls_reached"
                break
        else:
            stop_reason = "max_tool_iterations_reached"

        if stop_reason is not None:
            messages.append(
                LLMMessage(
                    role="user",
                    content=(
                        f"Tool execution stopped because {stop_reason}. Provide the best factual "
                        "program comparison from the observations already gathered. "
                        "If critical information "
                        "is missing, say it is not available in the current NNMC catalog or ask "
                        "for the missing filters."
                    ),
                )
            )
            final_response = await self.llm_provider.generate(
                LLMRequest(
                    messages=messages,
                    system_prompt=COMPARISON_ADVISOR_PROMPT,
                    tools=[],
                    metadata={"module": self.name, "tool_loop_exhausted": True},
                )
            )

        content = (
            final_response.content
            if final_response is not None and final_response.content
            else "I need more NNMC program information before I can answer factually."
        )
        return ModuleResponse(
            module_name=self.name,
            content=content,
            data={
                "observations": jsonable_encoder(observations),
                "tool_call_count": len(observations),
            },
            confidence=0.85 if final_response is not None else 0.45,
            metadata={
                "description": self.description,
                "advisor_prompt": "comparison.advisor",
                "available_tools": self.available_tool_names,
                "tool_invoked": observations[-1]["tool"] if observations else None,
                "tools_invoked": [observation["tool"] for observation in observations],
                "tool_budget": {
                    "max_tool_iterations": self.max_tool_iterations,
                    "max_total_tool_calls": self.max_total_tool_calls,
                    "max_same_tool_calls": self.max_same_tool_calls,
                    "stop_reason": stop_reason,
                },
            },
        )

    @property
    def available_tool_names(self) -> list[str]:
        return [tool.name for tool in get_tools()]

    @property
    def tool_schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in get_tools()
            if tool.name in SUPPORTED_TOOL_NAMES
        ]

    def _initial_messages(self, context: StudentContext, query: str) -> list[LLMMessage]:
        context_payload = {
            "user": context.user,
            "program": context.program,
            "university": context.university,
            "preferences": context.preferences,
            "memory": context.memory,
            "career_goal": context.career_goal,
            "available_tools": self.available_tool_names,
        }
        return [
            LLMMessage(
                role="user",
                content=(
                    f"Student query:\n{query}\n\n"
                    "Known student context:\n"
                    f"{json.dumps(jsonable_encoder(context_payload))}"
                ),
            )
        ]

    def _budgeted_tool_calls(
        self,
        tool_calls: list[dict[str, Any]],
        tool_counts: dict[str, int],
    ) -> list[dict[str, Any]]:
        allowed: list[dict[str, Any]] = []
        total_used = sum(tool_counts.values())
        for tool_call in tool_calls:
            if total_used + len(allowed) >= self.max_total_tool_calls:
                break
            tool_name = tool_call["name"]
            used_for_tool = tool_counts.get(tool_name, 0) + sum(
                1 for item in allowed if item["name"] == tool_name
            )
            if used_for_tool >= self.max_same_tool_calls:
                continue
            allowed.append(tool_call)
        return allowed

    async def _execute_tool_call(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        tool_name = tool_call["name"]
        if tool_name not in self.tools or tool_name not in SUPPORTED_TOOL_NAMES:
            return {
                "tool": tool_name,
                "success": False,
                "error": "Tool is not exposed to college comparison.",
            }
        if self.db is None:
            return {
                "tool": tool_name,
                "success": False,
                "error": "CollegeComparisonModule requires a database session.",
            }

        command = dict(tool_call["arguments"])
        try:
            result = await self._execute_tool(tool_name, command)
        except Exception as exc:
            return {
                "tool": tool_name,
                "success": False,
                "arguments": jsonable_encoder(command),
                "error": str(exc),
            }
        return {
            "tool": tool_name,
            "success": True,
            "arguments": jsonable_encoder(command),
            "result": jsonable_encoder(result),
        }

    def _tool_calls_from_response(self, response: LLMResponse) -> list[dict[str, Any]]:
        if response.tool_calls:
            return [
                {"id": tool_call.id, "name": tool_call.name, "arguments": tool_call.arguments}
                for tool_call in response.tool_calls
            ]

        parsed = _command_payload(response.content)
        raw_calls = parsed.get("tool_calls")
        if not isinstance(raw_calls, list):
            return []

        tool_calls = []
        for item in raw_calls:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("tool")
            arguments = item.get("arguments") or item.get("payload") or {}
            if isinstance(name, str) and isinstance(arguments, dict):
                tool_calls.append({"id": item.get("id"), "name": name, "arguments": arguments})
        return tool_calls

    async def _execute_tool(self, tool_name: str, command: dict[str, Any]) -> Any:
        tool = self.tools[tool_name]
        payload = _payload(command)
        if tool_name == "search_universities":
            return await tool.execute(self.db, payload)
        if tool_name == "compare_universities":
            return await tool.execute(self.db, command.get("university_ids") or payload)
        if tool_name == "search_programs":
            return await tool.execute(self.db, payload)
        if tool_name == "compare_programs":
            return await tool.execute(self.db, command.get("program_ids") or payload)
        if tool_name == "compare_career_paths":
            return await tool.execute(self.db, command.get("program_ids") or payload)
        raise ValueError(f"Unsupported college comparison tool: {tool_name}")


def _command_payload(query: str) -> dict[str, Any]:
    stripped = query.strip()
    if not stripped:
        return {}
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end <= start:
            return {}
        try:
            parsed = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError:
            return {}
    return parsed if isinstance(parsed, dict) else {}


def _payload(command: dict[str, Any]) -> dict[str, Any]:
    payload = command.get("payload", command)
    return payload if isinstance(payload, dict) else {}
