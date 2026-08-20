import axios from "axios";
import { API_BASE_URL } from "./apiBaseUrl.js";
import {
	INSTITUTION,
	isNorthernNewMexicoCollege,
} from "../config/institution.js";

const client = axios.create({
	baseURL: API_BASE_URL,
	timeout: 20000,
});

export const searchUniversities = async ({
	search = INSTITUTION.name,
	page = 0,
	perPage = 20,
} = {}) => {
	const response = await client.get("/universities", {
		params: {
			search: search || INSTITUTION.name,
			page,
			per_page: perPage,
		},
	});
	const data = (response.data?.data || []).filter((college) =>
		isNorthernNewMexicoCollege(college.name || college.university_name)
	);
	return { ...response.data, data };
};

export const getUniversityById = async (unitId) => {
	const response = await client.get(`/universities/${unitId}`);
	const college = response.data?.data || null;
	return college &&
		isNorthernNewMexicoCollege(college.name || college.university_name)
		? college
		: null;
};

export default {
	searchUniversities,
	getUniversityById,
};
