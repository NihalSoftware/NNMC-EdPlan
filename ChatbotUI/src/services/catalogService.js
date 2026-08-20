import axios from "axios";
import { API_BASE_URL } from "./apiBaseUrl.js";
import {
	INSTITUTION,
	isNorthernNewMexicoCollege,
} from "../config/institution.js";

const client = axios.create({
	baseURL: API_BASE_URL,
	timeout: 15000,
});

const unwrapData = (response) => response.data?.data || [];

export const getCatalogUniversities = async () => {
	const response = await client.get("/universities", {
		params: { search: INSTITUTION.name, per_page: 10 },
	});
	return unwrapData(response).filter((college) =>
		isNorthernNewMexicoCollege(college.name || college.university_name)
	);
};

export const getCatalogPrograms = async (universityId) => {
	const response = await client.get("/programs", {
		params: {
			university_id: universityId || undefined,
		},
	});
	return unwrapData(response).filter((program) =>
		isNorthernNewMexicoCollege(
			program.university_name ||
				program.university?.university_name ||
				program.university
		)
	);
};

export const getCatalogCourses = async (programId) => {
	const response = await client.get(`/programs/${programId}/courses`);
	return unwrapData(response);
};

export const getCareers = async () => {
	const response = await client.get("/careers");
	return unwrapData(response);
};

export default {
	getCatalogUniversities,
	getCatalogPrograms,
	getCatalogCourses,
	getCareers,
};

