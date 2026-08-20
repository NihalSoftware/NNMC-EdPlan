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
from app.student.domains.planning.tools.registry import PLANNING_TOOLS

MODULE_NAME = "academic_planning"

MODULE_DESCRIPTION = "Manage student education plans and graduation pathways."

ACADEMIC_PLANNING_ADVISOR_PROMPT = (
    "You are Northern New Mexico College's Academic Planning Advisor. "
    "Act as an NNMC academic advisor. "
    "Prioritize graduation feasibility, prerequisite compliance, corequisite compliance, "
    "and realistic academic load. Use only the exposed academic planning tools when "
    "information is required. Never invent completed courses, degree requirements, "
    "prerequisites, corequisites, validation results, or audit findings. If information "
    "is missing, retrieve it through tools or ask the student for the missing information. "
    "Prefer validated plans over assumptions. For complex advising workflows, attempt to "
    "compare Aggressive Plan, Balanced Plan, and Low-Risk Plan alternatives when sufficient "
    "information exists. Each plan should include semesters, courses, credit loads, "
    "prerequisite compliance, graduation impact, tradeoffs, and a ranked recommendation. "
    "For graduation acceleration requests: determine remaining requirements, prerequisite "
    "constraints, and corequisite constraints; generate multiple feasible plans when possible; "
    "validate plans before recommending; rank alternatives; explain tradeoffs; and state the "
    "expected graduation timeline. For planning/advising questions, prefer this format when "
    "enough information exists: Summary; Aggressive Plan with semesters and graduation "
    "estimate; Balanced Plan with semesters and graduation estimate; Low-Risk Plan with "
    "semesters and graduation estimate; Recommended Option; Reasoning. Do not force this "
    "format for simple CRUD requests."
)

SUPPORTED_TOOL_NAMES = {
    "create_plan",
    "update_plan",
    "delete_plan",
    "get_plan",
    "add_course",
    "remove_course",
    "move_course",
    "validate_plan",
    "audit_plan",
    "get_remaining_courses",
    "get_course_details",
    "get_prerequisites",
    "get_corequisites",
    "get_program_requirements",
    "get_available_terms",
}


def get_tools():
    return PLANNING_TOOLS


class AcademicPlanningModule(BaseModule):
    """Orchestrator module adapter for the existing academic planning tools."""

    name = MODULE_NAME
    description = MODULE_DESCRIPTION

    def __init__(
        self,
        db: AsyncSession | None = None,
        tools: list[Any] | None = None,
        llm_provider: BaseLLMProvider | None = None,
        max_tool_iterations: int = 6,
        max_total_tool_calls: int = 10,
        max_same_tool_calls: int = 2,
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
                    system_prompt=ACADEMIC_PLANNING_ADVISOR_PROMPT,
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
                    content=llm_response.content or "Requesting academic planning tools.",
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
                observation = await self._execute_tool_call(context, tool_call)
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
                        f"Tool execution stopped because {stop_reason}. Provide the best "
                        "academic advising response from the observations already gathered. "
                        "If critical information is still missing, ask the student for it "
                        "instead of guessing."
                    ),
                )
            )
            final_response = await self.llm_provider.generate(
                LLMRequest(
                    messages=messages,
                    system_prompt=ACADEMIC_PLANNING_ADVISOR_PROMPT,
                    tools=[],
                    metadata={"module": self.name, "tool_loop_exhausted": True},
                )
            )

        content = (
            final_response.content
            if final_response is not None and final_response.content
            else "I need more academic planning information before I can advise confidently."
        )
        return ModuleResponse(
            module_name=self.name,
            content=content,
            data={
                "observations": jsonable_encoder(observations),
                "tool_call_count": len(observations),
                "planning_summary": self._planning_summary(context),
            },
            confidence=0.85 if final_response is not None else 0.45,
            metadata={
                "description": self.description,
                "advisor_prompt": "academic_planning.advisor",
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
        planning_summary = self._planning_summary(context)
        context_payload = {
            "planning_summary": planning_summary,
            "user": context.user,
            "plan": context.plan,
            "program": context.program,
            "university": context.university,
            "completed_courses": context.completed_courses,
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
                    "Use this compact planning summary first to avoid unnecessary tool calls:\n"
                    f"{json.dumps(jsonable_encoder(planning_summary))}\n\n"
                    f"Known student context:\n{json.dumps(jsonable_encoder(context_payload))}"
                ),
            )
        ]

    def _planning_summary(self, context: StudentContext) -> dict[str, Any]:
        completed_courses = context.completed_courses or []
        plan = context.plan or {}
        payload = plan.get("payload") if isinstance(plan.get("payload"), dict) else {}
        planned_courses = payload.get("courses") if isinstance(payload, dict) else None
        if not isinstance(planned_courses, list):
            planned_courses = completed_courses

        completed_credits = _sum_credits(completed_courses)
        current_plan_credits = _sum_credits(planned_courses)
        return {
            "completed_courses": len(completed_courses),
            "remaining_courses": None,
            "completed_credits": completed_credits,
            "remaining_credits": None,
            "current_plan_courses": len(planned_courses),
            "current_plan_credits": current_plan_credits,
            "audit_status": "unknown_until_audit_tool_runs",
        }

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

    async def _execute_tool_call(
        self,
        context: StudentContext,
        tool_call: dict[str, Any],
    ) -> dict[str, Any]:
        tool_name = tool_call["name"]
        if tool_name not in self.tools or tool_name not in SUPPORTED_TOOL_NAMES:
            return {
                "tool": tool_name,
                "success": False,
                "error": "Tool is not exposed to academic planning.",
            }
        if self.db is None:
            return {
                "tool": tool_name,
                "success": False,
                "error": "AcademicPlanningModule requires a database session.",
            }

        command = dict(tool_call["arguments"])
        try:
            result = await self._execute_tool(tool_name, context, command)
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
                {
                    "id": tool_call.id,
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                }
                for tool_call in response.tool_calls
            ]

        parsed = self._command_payload(response.content)
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
                tool_calls.append(
                    {
                        "id": item.get("id"),
                        "name": name,
                        "arguments": arguments,
                    }
                )
        return tool_calls

    async def _execute_tool(
        self,
        tool_name: str,
        context: StudentContext,
        command: dict[str, Any],
    ) -> Any:
        tool = self.tools[tool_name]
        payload = self._payload(command)

        if tool_name == "create_plan":
            return await tool.execute(self.db, self._create_plan_payload(context, command, payload))
        if tool_name == "update_plan":
            plan_id = self._plan_id(context, command)
            return await tool.execute(self.db, plan_id, self._update_plan_payload(command, payload))
        if tool_name == "delete_plan":
            return await tool.execute(self.db, self._plan_id(context, command))
        if tool_name == "get_plan":
            return await tool.execute(self.db, self._plan_id(context, command))
        if tool_name == "add_course":
            plan_id = self._plan_id(context, command)
            return await tool.execute(
                self.db, plan_id, self._course_create_payload(command, payload)
            )
        if tool_name == "remove_course":
            return await tool.execute(
                self.db,
                self._plan_id(context, command),
                self._course_id(command, payload),
            )
        if tool_name == "move_course":
            return await tool.execute(
                self.db,
                self._plan_id(context, command),
                self._course_id(command, payload),
                self._course_update_payload(command, payload),
            )
        if tool_name == "validate_plan":
            return await tool.execute(self.db, self._plan_id(context, command), payload or None)
        if tool_name == "audit_plan":
            return await tool.execute(self.db, self._plan_id(context, command))
        if tool_name == "get_remaining_courses":
            return await tool.execute(self.db, self._plan_id(context, command))
        if tool_name == "get_course_details":
            return await tool.execute(self.db, self._course_id(command, payload))
        if tool_name == "get_prerequisites":
            return await tool.execute(self.db, self._course_id(command, payload))
        if tool_name == "get_corequisites":
            return await tool.execute(self.db, self._course_id(command, payload))
        if tool_name == "get_program_requirements":
            return await tool.execute(self.db, self._program_id(context, command, payload))
        if tool_name == "get_available_terms":
            return await tool.execute(self.db)

        raise ValueError(f"Unsupported academic planning tool: {tool_name}")

    @staticmethod
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

    @staticmethod
    def _payload(command: dict[str, Any]) -> dict[str, Any]:
        payload = command.get("payload", command)
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _plan_id(context: StudentContext, command: dict[str, Any]) -> str:
        plan = context.plan or {}
        plan_id = command.get("plan_id") or plan.get("plan_id")
        if not plan_id:
            raise ValueError("plan_id is required for this planning tool.")
        return str(plan_id)

    @staticmethod
    def _course_id(command: dict[str, Any], payload: dict[str, Any]) -> str:
        course_id = command.get("course_id") or payload.get("course_id")
        if not course_id:
            raise ValueError("course_id is required for this planning tool.")
        return str(course_id)

    @staticmethod
    def _program_id(
        context: StudentContext,
        command: dict[str, Any],
        payload: dict[str, Any],
    ) -> str:
        program = context.program or {}
        program_id = (
            command.get("program_id") or payload.get("program_id") or program.get("program_id")
        )
        if not program_id:
            raise ValueError("program_id is required for this planning tool.")
        return str(program_id)

    @staticmethod
    def _create_plan_payload(
        context: StudentContext,
        command: dict[str, Any],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        user = context.user or {}
        university = context.university or {}
        program = context.program or {}
        return {
            "user_id": payload.get("user_id") or command.get("user_id") or user.get("id"),
            "university_id": (
                payload.get("university_id")
                or command.get("university_id")
                or university.get("university_id")
                or university.get("id")
            ),
            "program_id": (
                payload.get("program_id")
                or command.get("program_id")
                or program.get("program_id")
                or program.get("id")
            ),
            "plan_name": payload.get("plan_name") or command.get("plan_name") or "Academic Plan",
            "description": payload.get("description") or command.get("description"),
            "is_active": payload.get("is_active", command.get("is_active", True)),
        }

    @staticmethod
    def _update_plan_payload(command: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "plan_name": payload.get("plan_name") or command.get("plan_name"),
                "description": payload.get("description") or command.get("description"),
                "is_active": payload.get("is_active", command.get("is_active")),
            }.items()
            if value is not None
        }

    @staticmethod
    def _course_create_payload(command: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "course_id": payload.get("course_id") or command.get("course_id"),
            "planned_term_id": payload.get("planned_term_id") or command.get("planned_term_id"),
            "status": payload.get("status") or command.get("status") or "Planned",
            "notes": payload.get("notes") or command.get("notes"),
        }

    @staticmethod
    def _course_update_payload(command: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "planned_term_id": payload.get("planned_term_id") or command.get("planned_term_id"),
                "status": payload.get("status") or command.get("status"),
                "notes": payload.get("notes") or command.get("notes"),
            }.items()
            if value is not None
        }


def _sum_credits(courses: list[dict[str, Any]]) -> int:
    total = 0
    for course in courses:
        credits = course.get("credits")
        if isinstance(credits, int):
            total += credits
        elif isinstance(credits, str) and credits.isdigit():
            total += int(credits)
    return total
