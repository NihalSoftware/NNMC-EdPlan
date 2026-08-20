from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models.agentic import ConversationMemory, StudentPreference
from app.orchestrator.memory.memory_manager import (
    CAREER_GOAL,
    CLASS_PREFERENCE,
    CREDIT_PREFERENCE,
    SCHEDULE_PREFERENCE,
    MemoryManager,
)
from app.orchestrator.schemas.module_response import FinalResponse


class FakeScalarResult:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items


class FakeResult:
    def __init__(self, items=None):
        self.items = items or []

    def scalars(self):
        return FakeScalarResult(self.items)


class FakeAsyncSession:
    def __init__(self, results=None) -> None:
        self.results = list(results or [])
        self.added = []
        self.commit_count = 0
        self.rollback_count = 0

    def add(self, item) -> None:
        self.added.append(item)

    async def execute(self, statement):
        if self.results:
            return self.results.pop(0)
        return FakeResult([])

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1


def test_extracts_career_goal():
    preferences = MemoryManager().extract_preferences("I want to become a Data Scientist.")

    assert preferences[CAREER_GOAL] == "Data Scientist"


def test_extracts_class_preference():
    preferences = MemoryManager().extract_preferences("I prefer morning classes.")

    assert preferences[CLASS_PREFERENCE] == "morning classes"


def test_extracts_credit_preference():
    preferences = MemoryManager().extract_preferences("I can handle 18 credits.")

    assert preferences[CREDIT_PREFERENCE] == "18 credits"


def test_extracts_schedule_preference():
    preferences = MemoryManager().extract_preferences("I do not want classes on Friday.")

    assert preferences[SCHEDULE_PREFERENCE] == "no classes on Friday"


@pytest.mark.asyncio
async def test_save_preferences_updates_existing_preference():
    existing = StudentPreference(
        preference_id=uuid4(),
        user_id=1,
        preference_key=CAREER_GOAL,
        preference_value="Cybersecurity",
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    session = FakeAsyncSession([FakeResult([existing])])

    saved = await MemoryManager(session).save_preferences(
        1,
        {CAREER_GOAL: "Data Scientist"},
    )

    assert saved == [existing]
    assert existing.preference_value == "Data Scientist"
    assert session.added == []
    assert session.commit_count == 1


def test_creates_deterministic_memory_summary():
    summary = MemoryManager().summarize_conversation(
        "I want to become an AI Engineer. I prefer morning classes.",
        FinalResponse(message="success"),
    )

    assert (
        summary
        == "Interested in AI Engineer career. Prefers morning classes. Response status: success."
    )


@pytest.mark.asyncio
async def test_save_memory_persists_summary():
    session = FakeAsyncSession()
    plan_id = uuid4()
    run_id = uuid4()

    memory = await MemoryManager(session).save_memory(
        user_id=1,
        plan_id=plan_id,
        run_id=run_id,
        summary="Interested in AI career.",
    )

    assert isinstance(memory, ConversationMemory)
    assert memory.plan_id == plan_id
    assert memory.run_id == run_id
    assert memory.summary == "Interested in AI career."
    assert session.added == [memory]
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_update_memory_persists_preferences_and_memory():
    session = FakeAsyncSession([FakeResult([])])
    plan_id = uuid4()
    run_id = uuid4()

    result = await MemoryManager(session).update_memory(
        user_id=1,
        plan_id=plan_id,
        run_id=run_id,
        query="I want to work in Cybersecurity. I only want 12 credits.",
        response=FinalResponse(message="success"),
    )

    preferences = [item for item in session.added if isinstance(item, StudentPreference)]
    memories = [item for item in session.added if isinstance(item, ConversationMemory)]
    assert result["preference_keys"] == [CAREER_GOAL, CREDIT_PREFERENCE]
    assert preferences[0].preference_value == "Cybersecurity"
    assert preferences[1].preference_value == "12 credits"
    assert memories[0].summary.startswith("Interested in Cybersecurity career.")
