export const CAREER_CATALOG_URL = "/assets/career_program_data.json";
export const CAREER_EMPLOYERS_URL = "/assets/career_employers.json";

const fetchJson = async (url) => {
	const response = await fetch(url, { signal: AbortSignal.timeout(15000) });
	if (!response.ok) throw new Error(`Unable to load ${url}`);
	return response.json();
};

export const loadCareerCatalog = async () => {
	const [catalog, employers] = await Promise.all([
		fetchJson(CAREER_CATALOG_URL),
		fetchJson(CAREER_EMPLOYERS_URL).catch(() => ({})),
	]);

	if (!catalog || !Array.isArray(catalog.degrees)) {
		throw new Error("Unexpected career catalog response");
	}

	return { catalog, employers };
};

export const getCareerArea = (programName = "") => {
	const value = String(programName).trim().toLowerCase();
	if (/education|teaching|child development|childhood/.test(value)) return "Education";
	if (/nursing|allied health|phlebotomy|health/.test(value)) return "Healthcare and Nursing";
	if (/criminal|justice|public administration/.test(value)) return "Public Service";
	if (/film|media|art|psychology|humanities|liberal|literary/.test(value)) return "Arts and Humanities";
	if (/business|account|management|administration|bookkeep|entrepreneur|hospitality/.test(value)) return "Business and Management";
	if (/computer|cyber|software|data|information engineering|mechanical engineering/.test(value)) return "Computer Science and Technology";
	if (/biology|chemistry|environment|mathematics|biotechnology|radiation|nuclear/.test(value)) return "Science and Environment";
	return "Skilled and Technical Trades";
};

const slugify = (value) =>
	String(value)
		.toLowerCase()
		.replace(/&/g, " and ")
		.replace(/[^a-z0-9]+/g, "-")
		.replace(/^-|-$/g, "");

const addUnique = (items, value, key) => {
	if (!value) return;
	const identity = key(value);
	if (!items.some((item) => key(item) === identity)) items.push(value);
};

export const buildCareerRecords = (catalog, employers = {}) => {
	const careerMap = new Map();

	(catalog?.degrees || []).forEach((degree) => {
		(degree.programs || []).forEach((program) => {
			const area = getCareerArea(program.name);
			(program.careers || []).forEach((career) => {
				const title = String(career.title || "").trim();
				if (!title) return;
				const mapKey = `${area}::${slugify(title)}`;
				if (!careerMap.has(mapKey)) {
					careerMap.set(mapKey, {
						id: `${slugify(area)}-${slugify(title)}`,
						title,
						area,
						salary: career.salary || "Not reported",
						description: career.description || "",
						pathways: [],
						competencies: [],
						employers: [],
					});
				}

				const record = careerMap.get(mapKey);
				addUnique(
					record.pathways,
					{ program: program.name, degree: degree.name },
					(pathway) => `${pathway.degree}::${pathway.program}`
				);
				(career.competencies || []).forEach((competency) => {
					const normalized =
						typeof competency === "string"
							? { topic: competency, description: catalog.competencies?.[competency] || "" }
							: {
									topic: competency?.topic || competency?.name || "",
									description:
										competency?.description ||
										catalog.competencies?.[competency?.topic || competency?.name] ||
										"",
							  };
					addUnique(record.competencies, normalized, (item) => item.topic.toLowerCase());
				});
				(employers?.[degree.name]?.[title] || []).forEach((employer) =>
					addUnique(record.employers, employer, (item) => item.toLowerCase())
				);
			});
		});
	});

	return [...careerMap.values()].sort(
		(a, b) => a.area.localeCompare(b.area) || a.title.localeCompare(b.title)
	);
};

export const countCareersByArea = (careers = []) =>
	careers.reduce((counts, career) => {
		counts[career.area] = (counts[career.area] || 0) + 1;
		return counts;
	}, {});
