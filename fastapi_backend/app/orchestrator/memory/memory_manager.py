from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Final
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agentic import ConversationMemory, StudentPreference
from app.orchestrator.schemas.module_response import FinalResponse

CAREER_GOAL: Final = "career_goal"
CLASS_PREFERENCE: Final = "class_preference"
CREDIT_PREFERENCE: Final = "credit_preference"
SCHEDULE_PREFERENCE: Final = "schedule_preference"


class MemoryManager:
    """Deterministic memory writer for student orchestrator conversations."""

    def __init__(self, db: AsyncSession | None = None) -> None:
        self.db = db

    async def get_preferences(self, user_id: int) -> list[StudentPreference]:
        if self.db is None:
            return []
        result = await self.db.execute(
            select(StudentPreference)
            .where(StudentPreference.user_id == user_id)
            .order_by(StudentPreference.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_memory(self, user_id: int, plan_id: UUID) -> list[ConversationMemory]:
        if self.db is None:
            return []
        result = await self.db.execute(
            select(ConversationMemory)
            .where(ConversationMemory.user_id == user_id, ConversationMemory.plan_id == plan_id)
            .order_by(ConversationMemory.created_at.desc())
        )
        return list(result.scalars().all())

    def extract_preferences(self, text: str) -> dict[str, str]:
        normalized_text = " ".join(text.strip().split())
        if not normalized_text:
            return {}

        preferences: dict[str, str] = {}
        career_goal = self._extract_career_goal(normalized_text)
        if career_goal is not None:
            preferences[CAREER_GOAL] = career_goal

        class_preference = self._extract_class_preference(normalized_text)
        if class_preference is not None:
            preferences[CLASS_PREFERENCE] = class_preference

        credit_preference = self._extract_credit_preference(normalized_text)
        if credit_preference is not None:
            preferences[CREDIT_PREFERENCE] = credit_preference

        schedule_preference = self._extract_schedule_preference(normalized_text)
        if schedule_preference is not None:
            preferences[SCHEDULE_PREFERENCE] = schedule_preference

        return preferences

    async def save_preferences(
        self,
        user_id: int,
        preferences: dict[str, str],
    ) -> list[StudentPreference]:
        if self.db is None or not preferences:
            return []

        existing_preferences = await self.get_preferences(user_id)
        existing_by_key = {
            preference.preference_key: preference for preference in existing_preferences
        }
        saved_preferences: list[StudentPreference] = []

        for key, value in preferences.items():
            preference = existing_by_key.get(key)
            if preference is None:
                preference = StudentPreference(
                    preference_id=uuid4(),
                    user_id=user_id,
                    preference_key=key,
                    preference_value=value,
                    updated_at=_utcnow(),
                )
                self.db.add(preference)
            else:
                preference.preference_value = value
                preference.updated_at = _utcnow()
            saved_preferences.append(preference)

        await self._commit()
        return saved_preferences

    def summarize_conversation(
        self,
        query: str,
        response: FinalResponse | None = None,
    ) -> str:
        preferences = self.extract_preferences(query)
        summary_parts: list[str] = []

        career_goal = preferences.get(CAREER_GOAL)
        if career_goal is not None:
            summary_parts.append(f"Interested in {career_goal} career.")

        class_preference = preferences.get(CLASS_PREFERENCE)
        if class_preference is not None:
            summary_parts.append(f"Prefers {class_preference}.")

        credit_preference = preferences.get(CREDIT_PREFERENCE)
        if credit_preference is not None:
            summary_parts.append(f"Credit preference: {credit_preference}.")

        schedule_preference = preferences.get(SCHEDULE_PREFERENCE)
        if schedule_preference is not None:
            summary_parts.append(f"Schedule preference: {schedule_preference}.")

        if not summary_parts:
            summary_parts.append(f"Student asked: {_compact_sentence(query)}.")

        if response is not None:
            summary_parts.append(f"Response status: {response.message}.")

        return " ".join(summary_parts)

    async def save_memory(
        self,
        user_id: int,
        plan_id: UUID,
        run_id: UUID,
        summary: str,
    ) -> ConversationMemory | None:
        if self.db is None or not summary.strip():
            return None

        memory = ConversationMemory(
            memory_id=uuid4(),
            user_id=user_id,
            plan_id=plan_id,
            run_id=run_id,
            summary=summary,
            created_at=_utcnow(),
        )
        self.db.add(memory)
        await self._commit()
        return memory

    async def update_memory(
        self,
        user_id: int,
        plan_id: UUID,
        run_id: UUID,
        query: str,
        response: FinalResponse | None,
    ) -> dict[str, object]:
        preferences = self.extract_preferences(query)
        saved_preferences = await self.save_preferences(user_id, preferences)
        summary = self.summarize_conversation(query, response)
        memory = await self.save_memory(user_id, plan_id, run_id, summary)
        return {
            "preference_count": len(saved_preferences),
            "preference_keys": list(preferences),
            "memory_saved": memory is not None,
            "summary": summary,
        }

    @staticmethod
    def _extract_career_goal(text: str) -> str | None:
        patterns = (
            r"\bi want to become an?\s+(?P<value>[^.?!,]+)",
            r"\bi want to become\s+(?P<value>[^.?!,]+)",
            r"\bi want to be an?\s+(?P<value>[^.?!,]+)",
            r"\bi want to work in\s+(?P<value>[^.?!,]+)",
            r"\bi want to work as an?\s+(?P<value>[^.?!,]+)",
        )
        return _first_match(text, patterns)

    @staticmethod
    def _extract_class_preference(text: str) -> str | None:
        lowered = text.lower()
        for period in ("morning", "afternoon", "evening", "night", "online", "in-person"):
            if re.search(rf"\b(?:prefer|like)\s+{re.escape(period)}\s+classes\b", lowered):
                return f"{period} classes"
        return None

    @staticmethod
    def _extract_credit_preference(text: str) -> str | None:
        match = re.search(
            r"\b(?:i\s+)?(?:only\s+want|want|can\s+handle)\s+(?P<credits>\d{1,2})\s+credits?\b",
            text.lower(),
        )
        if match is None:
            return None
        return f"{match.group('credits')} credits"

    @staticmethod
    def _extract_schedule_preference(text: str) -> str | None:
        lowered = text.lower()
        no_day_match = re.search(
            r"\bi\s+(?:do not|don't)\s+want\s+classes\s+on\s+"
            r"(?P<day>monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            lowered,
        )
        if no_day_match is not None:
            return f"no classes on {no_day_match.group('day').title()}"
        if re.search(r"\bprefer\s+compact\s+schedules?\b", lowered):
            return "compact schedules"
        return None

    async def _commit(self) -> None:
        if self.db is None:
            return
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise


def _first_match(text: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match is not None:
            return _clean_value(match.group("value"))
    return None


def _clean_value(value: str) -> str:
    cleaned = value.strip(" .?!,;:")
    return " ".join(word if word.isupper() else word.capitalize() for word in cleaned.split())


def _compact_sentence(value: str) -> str:
    compacted = " ".join(value.strip(" .?!").split())
    if len(compacted) > 120:
        return f"{compacted[:117].rstrip()}..."
    return compacted


def _utcnow() -> datetime:
    return datetime.now(UTC)
