export const MAX_COMPARE_PROGRAMS = 3;

const normalize = (value) => String(value ?? "").trim().toLocaleLowerCase();

export const filterPrograms = (programs, filters = {}) => {
	const query = normalize(filters.query);
	const area = normalize(filters.area);
	const degreeType = normalize(filters.degreeType);
	const delivery = normalize(filters.delivery);
	const location = String(filters.location ?? "");
	const [locationType, ...locationParts] = location.split(":");
	const locationValue = normalize(locationParts.join(":"));

	return programs.filter((program) => {
		const searchable = normalize(
			[
				program.name,
				program.institution,
				program.state,
				program.area,
				program.degreeType,
				program.delivery,
				program.description,
				...(program.careers ?? []),
			].join(" ")
		);

		if (query && !searchable.includes(query)) return false;
		if (area && normalize(program.area) !== area) return false;
		if (degreeType && normalize(program.degreeType) !== degreeType) return false;
		if (delivery && normalize(program.delivery) !== delivery) return false;
		if (locationType === "state" && locationValue && normalize(program.state) !== locationValue) return false;
		if (
			locationType === "institution" &&
			locationValue &&
			normalize(program.institution) !== locationValue
		) {
			return false;
		}

		return true;
	});
};

export const toggleComparedProgram = (
	selectedIds,
	programId,
	limit = MAX_COMPARE_PROGRAMS
) => {
	if (selectedIds.includes(programId)) {
		return selectedIds.filter((id) => id !== programId);
	}

	if (selectedIds.length >= limit) return selectedIds;
	return [...selectedIds, programId];
};

export const uniqueSortedValues = (programs, key) =>
	Array.from(new Set(programs.map((program) => program[key]).filter(Boolean))).sort((a, b) =>
		a.localeCompare(b)
	);

export const hasActiveProgramFilters = (filters = {}) =>
	Boolean(
		filters.query ||
			filters.area ||
			filters.degreeType ||
			filters.delivery ||
			filters.location
	);
