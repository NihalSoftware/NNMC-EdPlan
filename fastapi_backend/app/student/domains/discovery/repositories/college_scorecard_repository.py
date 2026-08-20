from app.student.domains.discovery.clients.college_scorecard import CollegeScorecardClient, client


async def search_schools(
    *,
    search: str | None = None,
    state: str | None = None,
    page: int = 0,
    per_page: int = 25,
    scorecard_client: CollegeScorecardClient = client,
) -> dict:
    return await scorecard_client.search_schools(
        search=search,
        state=state,
        page=page,
        per_page=per_page,
    )


async def get_school(
    unit_id: str,
    *,
    scorecard_client: CollegeScorecardClient = client,
) -> dict | None:
    return await scorecard_client.get_school(unit_id)


async def compare_schools(
    unit_ids: list[int],
    *,
    scorecard_client: CollegeScorecardClient = client,
) -> list[dict]:
    results = []
    for unit_id in unit_ids:
        school = await scorecard_client.get_school(str(unit_id))
        if school:
            results.append(school)
    return results
