import axios from "axios";
import { loadSession } from "../utils/storage.js";
import { API_BASE_URL } from "./apiBaseUrl.js";

const client = axios.create({
	baseURL: API_BASE_URL,
	timeout: 15000,
	headers: {
		"Content-Type": "application/json",
	},
});

client.interceptors.request.use((config) => {
	const token = loadSession("AuthToken");
	if (token) {
		config.headers = config.headers ?? {};
		if (!config.headers.Authorization) {
			config.headers.Authorization = `Bearer ${token}`;
		}
	}
	return config;
});

export const login = ({ email, password }) =>
	client.post("/users/login", {
		email,
		password,
	});

export const register = ({
	firstName,
	lastName,
	email,
	phoneNumber,
	password,
}) =>
	client.post("/users", {
		first_name: firstName,
		last_name: lastName,
		email,
		phone_number: phoneNumber,
		password,
	});

export const addEducationPlan = ({
	email,
	program,
	rescheduledata,
	reschedule,
	degree,
}) =>
	client.post("/users/education-plan", {
		emailaddress: email,
		program,
		rescheduledata,
		reschedule,
		degree,
	});

export const getEducationPlanList = (email) => {
	const normalizedEmail = typeof email === "string" ? email : email?.email;
	return client.post("/users/education-plan/list", { email: normalizedEmail });
};

export const deleteEducationPlan = ({
	email,
	programName,
	universityName,
	degree,
}) =>
	client.post("/users/education-plan/delete", {
		email,
		programname: programName,
		univerityname: universityName,
		degree,
	});

export default client;
