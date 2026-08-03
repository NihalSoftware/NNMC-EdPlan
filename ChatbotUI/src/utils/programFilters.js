const normalize = (value) => String(value ?? "").trim().toLocaleLowerCase();

export const filterPrograms = (programs, filters = {}) => {
	const query = normalize(filters.query);
	const area = normalize(filters.area);
	const degreeType = normalize(filters.degreeType);

	return programs.filter((program) => {
		const searchable = normalize(
			[
				program.name,
				program.institution,
				program.state,
				program.area,
				program.degreeType,
				program.catalogCategory,
				program.description,
				...(program.careers ?? []),
			].join(" ")
		);

		if (query && !searchable.includes(query)) return false;
		if (area && normalize(program.area) !== area) return false;
		if (degreeType && normalize(program.degreeType) !== degreeType) return false;

		return true;
	});
};

export const uniqueSortedValues = (programs, key) =>
	Array.from(new Set(programs.map((program) => program[key]).filter(Boolean))).sort((a, b) =>
		a.localeCompare(b)
	);

export const hasActiveProgramFilters = (filters = {}) =>
	Boolean(
		filters.query ||
			filters.area ||
			filters.degreeType
	);
