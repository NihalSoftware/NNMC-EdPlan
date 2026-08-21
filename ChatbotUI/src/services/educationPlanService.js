import {
	getCatalogCourses,
	getCatalogPrograms,
} from "./catalogService.js";
import {
	INSTITUTION,
	isNorthernNewMexicoCollege,
} from "../config/institution.js";

let educationCache = null;
let educationWithCoursesCache = null;

const YEAR_LABELS = {
	1: "First Year",
	2: "Second Year",
	3: "Third Year",
	4: "Fourth Year",
	5: "Fifth Year",
	6: "Sixth Year",
	7: "Seventh Year",
	8: "Eighth Year",
};

const displayUniversityName = (name = "") => {
	const cleaned = String(name || "").trim();
	return isNorthernNewMexicoCollege(cleaned) ? INSTITUTION.name : cleaned;
};

const normalizeCourse = (course) => {
	const metadata = course.metadata_json || {};
	const requirements =
		course.requirement_occurrences || metadata.requirement_occurrences || [];

	return {
		id: course.course_id || course.id,
		code: course.course_code || course.code,
		name: course.course_name || course.name || course.courseName,
		courseName: course.course_name || course.courseName || course.name,
		credits: course.credits,
		credits_min: course.credits_min ?? metadata.credits_min ?? course.credits,
		credits_max: course.credits_max ?? metadata.credits_max ?? course.credits,
		credit_text:
			course.credit_text ||
			metadata.catalog_credit_text ||
			(course.credits == null ? "" : `${course.credits} CR`),
		credit_contact_text: metadata.credit_contact_text || "",
		lecture_hours:
			metadata.lecture_hours_exact ?? course.lecture_hours,
		lab_hours: metadata.lab_hours_exact ?? course.lab_hours,
		prerequisite: course.prerequisite || metadata.prerequisite || "",
		corequisite: course.corequisite || metadata.corequisite || "",
		pre_or_corequisite:
			course.pre_or_corequisite || metadata.pre_or_corequisite || "",
		requirement_expressions:
			course.requirement_expressions || metadata.requirement_expressions || {},
		recommended_year:
			YEAR_LABELS[course.recommended_year] ||
			course.recommended_year ||
			course.year ||
			"Unassigned Year",
		recommended_semester:
			course.recommended_semester || course.semester || "Unassigned Semester",
		is_elective: course.is_elective === true || metadata.is_elective === true,
		default_plan_eligible: course.default_plan_eligible === true,
		description: course.description || metadata.fields?.description || "",
		catalog_url: course.catalog_url || metadata.catalog_url || "",
		requirement_occurrences: requirements,
		official_source_id:
			course.official_source_id || metadata.catalog_course_id || "",
		official_source_url:
			course.official_source_url || course.catalog_url || metadata.catalog_url || "",
		source_retrieved_at:
			course.source_retrieved_at || metadata.source_retrieved_at || "",
		metadata_json: metadata,
		source_sequence: course.source_sequence,
	};
};

const groupCoursesByTerm = (courses = []) => {
	const yearMap = new Map();

	courses.forEach((course) => {
		const year = course.recommended_year || course.year || "Unassigned Year";
		const semester =
			course.recommended_semester || course.semester || "Unassigned Semester";

		if (!yearMap.has(year)) {
			yearMap.set(year, new Map());
		}
		const semesterMap = yearMap.get(year);
		if (!semesterMap.has(semester)) {
			semesterMap.set(semester, []);
		}
		semesterMap.get(semester).push(course);
	});

	return Array.from(yearMap.entries()).map(([year, semesterMap]) => ({
		year,
		semesters: Array.from(semesterMap.entries()).map(
			([semester, semesterCourses]) => ({
				semester,
				courses: semesterCourses,
			})
		),
	}));
};

const getUniversityPayload = (program) =>
	program.university && typeof program.university === "object"
		? program.university
		: {};

const normalizeProgram = (program, courses = []) => {
	const university = getUniversityPayload(program);
	const universityName = displayUniversityName(
		program.university_name ||
			university.university_name ||
			program.campus ||
			(typeof program.university === "string" ? program.university : "")
	);
	const normalizedCourses = courses.map(normalizeCourse);

	return {
		...program,
		program_id: program.program_id,
		program: program.program || program.program_name || "",
		program_name: program.program_name || program.program || "",
		university: universityName,
		campus: universityName,
		degree: program.degree || "",
		total_credit_hours: program.total_credit_hours,
		total_credit_hours_text:
			program.total_credit_hours_text ||
			program.metadata_json?.catalog_total_credits_text ||
			"",
		total_credit_hours_min:
			program.total_credit_hours_min ??
			program.metadata_json?.catalog_total_credits_min ??
			program.total_credit_hours,
		total_credit_hours_max:
			program.total_credit_hours_max ??
			program.metadata_json?.catalog_total_credits_max ??
			program.total_credit_hours,
		catalog_title:
			program.catalog_title || program.metadata_json?.catalog_title || "",
		catalog_url:
			program.catalog_url || program.metadata_json?.catalog_url || "",
		catalog_year:
			program.catalog_year || program.metadata_json?.catalog_year || "",
		catalog_program_id:
			program.catalog_program_id ||
			program.metadata_json?.catalog_program_id ||
			"",
		description:
			program.description ||
			(program.metadata_json?.catalog_intro || []).join("\n\n"),
		metadata_json: program.metadata_json || {},
		college_profile: {
			...(program.college_profile || {}),
			university_id: university.university_id || program.university_id,
			university_name: universityName,
			city: university.city || program.city || program.college_profile?.city,
			state: university.state || program.state || program.college_profile?.state,
			website:
				university.website || program.website || program.college_profile?.website,
		},
		courses: normalizedCourses,
		years: normalizedCourses.length
			? groupCoursesByTerm(normalizedCourses)
			: program.years || [],
	};
};

const loadPrograms = async ({ includeCourses = false } = {}) => {
	if (includeCourses && educationWithCoursesCache) return educationWithCoursesCache;
	if (!includeCourses && educationCache) return educationCache;

	const programs = await getCatalogPrograms();
	const normalizedPrograms = programs
		.map((program) => normalizeProgram(program))
		.filter((program) => isNorthernNewMexicoCollege(program.university));

	if (!includeCourses) {
		educationCache = normalizedPrograms;
		return educationCache;
	}

	educationWithCoursesCache = await Promise.all(
		normalizedPrograms.map((program) => getProgramWithCourses(program.program_id))
	);
	educationCache = educationCache || educationWithCoursesCache;
	return educationWithCoursesCache;
};

export const getProgramCourses = async (programId) => {
	const courses = await getCatalogCourses(programId);
	return courses.map(normalizeCourse);
};

export const getProgramWithCourses = async (programId) => {
	const programs = educationCache || (await loadPrograms());
	const program = programs.find((entry) => entry.program_id === programId);
	if (!program) return null;
	const courses = await getProgramCourses(programId);
	return normalizeProgram(program, courses);
};

export const findProgramPlan = async (programName, universityName) => {
	const normalizedUniversityName = isNorthernNewMexicoCollege(universityName)
		? INSTITUTION.name
		: "";
	if (!normalizedUniversityName) return null;
	const programs = await loadPrograms({ includeCourses: true });
	return (
		programs.find(
			(program) =>
				program.program === programName &&
				program.university === normalizedUniversityName
		) || null
	);
};

export const listPrograms = async (options) => loadPrograms(options);

