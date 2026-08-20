from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from time import perf_counter

from app.student.domains.scheduling.engine.candidate_models import (
    ScheduleCandidate,
    ScheduleGenerationMetadata,
    ScheduleGenerationResult,
)
from app.student.domains.scheduling.engine.generator_config import ScheduleGeneratorConfig
from app.student.domains.scheduling.schemas.schedulepilot import (
    ScheduleCourse,
    ScheduleCourseOffering,
    ScheduleMeeting,
    ScheduleRetrievalContext,
    ScheduleSection,
)


@dataclass(frozen=True)
class _CourseOption:
    course: ScheduleCourse
    sections: tuple[ScheduleSection, ...]
    meetings: tuple[ScheduleMeeting, ...]
    component_keys: tuple[str, ...]


class CandidateGenerator:
    """Deterministically generates schedule candidates from retrieval contracts."""

    def __init__(self, config: ScheduleGeneratorConfig | None = None) -> None:
        self.config = config or ScheduleGeneratorConfig()

    def generate(self, context: ScheduleRetrievalContext) -> ScheduleGenerationResult:
        started_at = perf_counter()
        warnings: list[str] = []
        course_options = self._course_options(context, warnings)
        candidates: list[ScheduleCandidate] = []
        seen_signatures: set[tuple[str, ...]] = set()
        truncated = False

        if course_options:
            for option_set in product(*course_options):
                signature = tuple(
                    section.section_id for option in option_set for section in option.sections
                )
                if signature in seen_signatures:
                    continue
                seen_signatures.add(signature)
                candidates.append(self._candidate(len(candidates) + 1, option_set))
                if len(candidates) >= self.config.max_candidate_count:
                    truncated = True
                    break

        generation_time_ms = max(0, round((perf_counter() - started_at) * 1000))
        return ScheduleGenerationResult(
            candidates=candidates,
            metadata=ScheduleGenerationMetadata(
                generated_count=len(candidates),
                truncated=truncated,
                generation_time_ms=generation_time_ms,
                max_candidate_count=self.config.max_candidate_count,
                course_count=len(context.courses),
                section_count=len(context.sections),
            ),
            warnings=warnings,
        )

    def _course_options(
        self,
        context: ScheduleRetrievalContext,
        warnings: list[str],
    ) -> list[list[_CourseOption]]:
        offering_by_id = {offering.offering_id: offering for offering in context.offerings}
        meetings_by_section_id: dict[str, list[ScheduleMeeting]] = {}
        for meeting in context.meetings:
            meetings_by_section_id.setdefault(meeting.section_id, []).append(meeting)

        all_course_options: list[list[_CourseOption]] = []
        for course in context.courses:
            course_offerings = [
                offering for offering in context.offerings if offering.course_id == course.course_id
            ]
            if not course_offerings:
                warnings.append(f"No offerings found for course {course.course_id}.")
                return []

            component_keys = _component_keys(course_offerings)
            component_section_groups: list[list[ScheduleSection]] = []
            for component_key in component_keys:
                offering_ids = {
                    offering.offering_id
                    for offering in course_offerings
                    if offering.offering_type == component_key
                }
                sections = [
                    section
                    for section in context.sections
                    if section.offering_id in offering_ids
                    and offering_by_id.get(section.offering_id) is not None
                ]
                sections = sorted(sections, key=lambda item: (item.section_number, item.section_id))
                if not sections:
                    warnings.append(
                        "No sections found for course "
                        f"{course.course_id} component {component_key}."
                    )
                    return []
                component_section_groups.append(sections)

            course_options = [
                _CourseOption(
                    course=course,
                    sections=tuple(section_set),
                    meetings=tuple(
                        meeting
                        for section in section_set
                        for meeting in meetings_by_section_id.get(section.section_id, [])
                    ),
                    component_keys=tuple(component_keys),
                )
                for section_set in product(*component_section_groups)
            ]
            all_course_options.append(course_options)
        return all_course_options

    @staticmethod
    def _candidate(index: int, option_set: tuple[_CourseOption, ...]) -> ScheduleCandidate:
        courses = [option.course for option in option_set]
        sections = [section for option in option_set for section in option.sections]
        meetings = [meeting for option in option_set for meeting in option.meetings]
        return ScheduleCandidate(
            candidate_id=f"candidate-{index:06d}",
            courses=courses,
            sections=sections,
            meetings=meetings,
            conflicts=[],
            warnings=[],
            metadata={
                "course_count": len(courses),
                "section_count": len(sections),
                "meeting_count": len(meetings),
                "component_count": sum(len(option.component_keys) for option in option_set),
            },
        )


def _component_keys(offerings: list[ScheduleCourseOffering]) -> list[str]:
    keys: list[str] = []
    for offering in offerings:
        if offering.offering_type not in keys:
            keys.append(offering.offering_type)
    return keys
