import { Fragment, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { jsPDF } from "jspdf";
import {
	deleteEducationPlan,
	getEducationPlanList,
} from "../../services/authService.js";
import { listPrograms } from "../../services/educationPlanService.js";
import {
	load as loadStorage,
	save as saveStorage,
} from "../../utils/storage.js";
import {
	INSTITUTION,
	isNorthernNewMexicoCollege,
} from "../../config/institution.js";

const normalizeRequirement = (value) => (value || "").trim();
const hasMeaningfulRequirement = (value) => {
	const normalized = normalizeRequirement(value).toLowerCase();
	return normalized && normalized !== "none" && normalized !== "n/a";
};

const CourseMeta = ({ course }) => {
	const prereqText = normalizeRequirement(course.prerequisite);
	const coreqText = normalizeRequirement(course.corequisite);
	const showPrereq = hasMeaningfulRequirement(prereqText);
	const showCoreq = hasMeaningfulRequirement(coreqText);

	return (
		<div className="text-xs text-slate-600 flex flex-wrap items-center gap-x-4 gap-y-1">
			<span className="inline-flex items-center gap-1 whitespace-nowrap">
				<span className="text-slate-500">Code:</span>
				<span className="font-medium text-slate-800">{course.code}</span>
			</span>
			<span className="inline-flex items-center gap-1 whitespace-nowrap">
				<span className="text-slate-500">Credits:</span>
				<span className="font-medium text-slate-800">
					{course.credits ?? "Not reported"}
				</span>
			</span>
			<span className="inline-flex items-center gap-1 whitespace-nowrap">
				<span className="text-sky-700">Pre-requisite:</span>
				<span
					className={
						showPrereq ? "text-orange-500 font-medium" : "text-slate-500"
					}
				>
					{prereqText || "None reported"}
				</span>
			</span>
			{showCoreq && (
				<span className="inline-flex items-center gap-1 whitespace-nowrap">
					<span className="text-sky-700">Corequisite:</span>
					<span className="text-yellow-500 font-medium">{coreqText}</span>
				</span>
			)}
		</div>
	);
};

const ViewEducationPlan = () => {
	const [savedPlans, setSavedPlans] = useState([]);
	const [programCatalogue, setProgramCatalogue] = useState([]);
	const [error, setError] = useState("");
	const [expandedPlanId, setExpandedPlanId] = useState(null);
	const [deletingPlanId, setDeletingPlanId] = useState(null);
	const [deleteTarget, setDeleteTarget] = useState(null);
	const storedEmail = loadStorage("UserEmail");
	const userEmail =
		typeof storedEmail === "string" ? storedEmail : storedEmail?.email;
	const navigate = useNavigate();

	const resolveDegree = (plan) => {
		const inline =
			plan.degree ||
			plan.program_degree ||
			plan.programDegree ||
			plan.program_meta?.degree ||
			"";
		if (inline) return inline;
		const match = programCatalogue.find(
			(entry) =>
				String(entry.university).toLowerCase() ===
					String(plan.university).toLowerCase() &&
				String(entry.program).toLowerCase() ===
					String(plan.program).toLowerCase()
		);
		return match?.degree || "";
	};
	const handleEdit = (plan) => {
		const degree = resolveDegree(plan);
		saveStorage("University", INSTITUTION.name);
		saveStorage("Programname", plan.program || "");
		saveStorage("ProgramDegree", degree || "");
		saveStorage("SelectedProgram", plan.program || "");
		saveStorage("SelectedDegreeLevel", degree || "");
		saveStorage("EditingPlan", {
			university: INSTITUTION.name,
			program: plan.program || "",
			degree: degree || "",
			courses: plan.courses || [],
			source: plan.source || "",
		});
		saveStorage("EditingPlanActive", true);
		navigate("/educationplan");
	};

	const loadLocalPlans = () => {
		const stored = loadStorage("LocalSavedPlans", []);
		return stored.map((entry, index) => ({
			id: `local-${index}`,
			university: entry.university || "",
			program: entry.program || "Program",
			degree:
				entry.degree ||
				entry.programDegree ||
				entry.program_degree ||
				entry.program_meta?.degree ||
				"",
			savedDate: entry.savedDate || new Date().toISOString(),
			courses: entry.courses || [],
			averageAnnualCost: entry.averageAnnualCost || "",
			source: "local",
		})).filter((plan) => isNorthernNewMexicoCollege(plan.university));
	};

	const loadPlans = async () => {
		const localPlans = loadLocalPlans();
		if (!userEmail) {
			setSavedPlans(localPlans);
			return;
		}
		setError("");
		try {
			const response = await getEducationPlanList(userEmail);
			const payload = response.data?.data || [];

			const remotePlans = payload.map((entry, index) => {
				const courses = entry.program || entry.courses || [];
				const firstCourse = courses.find(Boolean);
				return {
					id: `remote-${index}`,
					university:
						entry.university ||
						entry.university_name ||
						firstCourse?.university ||
						"",
					program:
						entry.program_name ||
						entry.programTitle ||
						firstCourse?.program ||
						"Program",
					degree:
						entry.program_meta?.degree ||
						entry.program_degree ||
						entry.degree ||
						"",
					savedDate:
						entry.created_at || entry.savedDate || new Date().toISOString(),
					courses,
					averageAnnualCost:
						entry.average_annual_cost ||
						entry.averageAnnualCost ||
						entry.college_profile?.average_annual_cost ||
						"",
					source: "remote",
				};
			}).filter((plan) => isNorthernNewMexicoCollege(plan.university));

			setSavedPlans([...remotePlans, ...localPlans]);
		} catch (err) {
			if (err.response?.status === 401) {
				setError(
					"Your session has expired. Please login again to view saved plans."
				);
			} else if (err.response?.status === 422) {
				setError("Unable to load saved plans. Please login again and retry.");
			} else {
				setError("Unable to fetch education plans at the moment.");
			}
			setSavedPlans(localPlans);
		}
	};

	useEffect(() => {
		loadPlans();
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [userEmail]);

	useEffect(() => {
		listPrograms()
			.then((items) => setProgramCatalogue(items))
			.catch(() => setProgramCatalogue([]));
	}, []);

	const getTotalCredits = (courses) => {
		return courses.reduce((sum, course) => {
			const value = Number(course.credits);
			return sum + (Number.isFinite(value) ? value : 0);
		}, 0);
	};

	const groupCoursesByYearAndSemester = (courses) => {
		return courses.reduce((acc, course) => {
			const year = course.year || "Year 1";
			const semester = course.semester || "Semester 1";
			acc[year] = acc[year] || {};
			acc[year][semester] = acc[year][semester] || [];
			acc[year][semester].push(course);
			return acc;
		}, {});
	};

	const findAverageAnnualCost = (plan) => {
		if (!plan.university || !plan.program) return null;
		const match = programCatalogue.find(
			(entry) =>
				String(entry.university).toLowerCase() ===
					String(plan.university).toLowerCase() &&
				String(entry.program).toLowerCase() ===
					String(plan.program).toLowerCase()
		);
		return (
			plan.average_annual_cost ||
			plan.averageAnnualCost ||
			match?.average_annual_cost ||
			match?.averageAnnualCost ||
			match?.college_profile?.average_annual_cost
		);
	};

	const handleDeletePlan = (plan) => {
		setDeleteTarget(plan);
	};

	const confirmDeletePlan = async () => {
		if (!deleteTarget) return;
		const plan = deleteTarget;

		if (plan.source === "local") {
			setSavedPlans((prev) => prev.filter((item) => item.id !== plan.id));
			const stored = loadStorage("LocalSavedPlans", []);
			const updated = stored.filter(
				(entry, index) => `local-${index}` !== plan.id
			);
			saveStorage("LocalSavedPlans", updated);
			setDeleteTarget(null);
			return;
		}

		if (!userEmail) {
			setError("Please login again to delete saved plans.");
			setDeleteTarget(null);
			return;
		}

		setError("");
		setDeletingPlanId(plan.id);
		try {
			await deleteEducationPlan({
				email: userEmail,
				programName: plan.program,
				universityName: plan.university,
			});
			setSavedPlans((prev) => prev.filter((item) => item.id !== plan.id));
		} catch (err) {
			if (err.response?.status === 401) {
				setError(
					"Your session has expired. Please login again to manage saved plans."
				);
			} else if (err.response?.status === 404) {
				setError("This saved plan was not found. Please refresh and retry.");
			} else {
				setError("Unable to delete the saved plan at the moment.");
			}
		} finally {
			setDeletingPlanId(null);
			setDeleteTarget(null);
		}
	};

	const closeDeleteModal = (event) => {
		if (deletingPlanId) return;
		if (!event || event.target === event.currentTarget) {
			setDeleteTarget(null);
		}
	};

	const toggleExpand = (planId) => {
		setExpandedPlanId((prev) => (prev === planId ? null : planId));
	};

	const downloadPlan = (plan) => {
		const doc = new jsPDF();
		let y = 12;

		const addLine = (text, options = {}) => {
			const lines = doc.splitTextToSize(String(text || ""), 180);
			lines.forEach((line) => {
				if (y > 280) {
					doc.addPage();
					y = 12;
				}
				doc.text(line, 14, y, options);
				y += 6;
			});
		};
		// Helper function to extract year number from year strings
		const getYearOrder = (yearStr) => {
			const yearMap = {
				first: 1,
				second: 2,
				third: 3,
				fourth: 4,
				fifth: 5,
				sixth: 6,
			};
			const lower = String(yearStr).toLowerCase();
			for (const [key, value] of Object.entries(yearMap)) {
				if (lower.includes(key)) return value;
			}
			// Try to extract number from "Year 1", "Year 2", etc.
			const match = lower.match(/year\s*(\d+)/);
			if (match) return parseInt(match[1], 10);
			return 999; // Unknown years go to the end
		};
		const grouped = groupCoursesByYearAndSemester(plan.courses || []);
		const totalCredits = getTotalCredits(plan.courses || []);
		const totalCourses = plan.courses?.length || 0;
		const degree = resolveDegree(plan);

		doc.setFontSize(14);
		addLine(`Education Plan: ${plan.program || "Program"}`);
		doc.setFontSize(11);
		addLine(`Institution: ${INSTITUTION.name}`);
		if (degree) addLine(`Degree: ${degree}`);
		addLine(`Total Credits: ${totalCredits}`);
		addLine(`Total Courses: ${totalCourses}`);
		addLine(" ");

		Object.keys(grouped)
			.sort((a, b) => getYearOrder(a) - getYearOrder(b))
			.forEach((yearKey) => {
				doc.setFontSize(12);
				addLine(yearKey);
				const semesters = grouped[yearKey] || {};
				Object.keys(semesters)
					.sort()
					.forEach((semKey) => {
						doc.setFontSize(11);
						addLine(`  ${semKey}`);
						doc.setFontSize(10);
						semesters[semKey].forEach((course) => {
							const prereq = normalizeRequirement(course.prerequisite);
							const coreq = normalizeRequirement(course.corequisite);
							addLine(
								`    • ${course.code || ""} — ${
									course.courseName || course.name || "Course"
								} (${course.credits ?? "credits not reported"}${course.credits == null ? "" : " credits"})`
							);
							if (hasMeaningfulRequirement(prereq)) {
								addLine(`      Prerequisite: ${prereq}`);
							}
							if (hasMeaningfulRequirement(coreq)) {
								addLine(`      Corequisite: ${coreq}`);
							}
						});
						addLine(" ");
					});
			});

		doc.save(`${plan.program || "education-plan"}.pdf`);
	};

	return (
		<>
			{deleteTarget && (
				<div
					className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4"
					onClick={closeDeleteModal}
				>
					<div
						className="w-full max-w-sm rounded-2xl bg-white shadow-xl border border-slate-200"
						role="dialog"
						aria-modal="true"
						aria-labelledby="delete-plan-title"
					>
						<div className="px-9 py-4">
							<h2
								id="delete-plan-title"
								className="text-lg font-semibold text-slate-900"
							>
								You are about to delete a saved plan
							</h2>
						</div>

						<div className="mb-4 flex items-center justify-center gap-4">
							<button
								type="button"
								onClick={closeDeleteModal}
								disabled={deletingPlanId === deleteTarget.id}
								className="px-4 py-2 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-200 disabled:cursor-not-allowed disabled:text-slate-400"
							>
								Cancel
							</button>
							<button
								type="button"
								onClick={confirmDeletePlan}
								disabled={deletingPlanId === deleteTarget.id}
								className="px-4 py-2 rounded-lg bg-rose-600 text-white hover:bg-rose-700 disabled:cursor-not-allowed disabled:bg-rose-300"
							>
								{deletingPlanId === deleteTarget.id
									? "Deleting..."
									: "Delete Plan"}
							</button>
						</div>
					</div>
				</div>
			)}
			<section className="space-y-6">
				<header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
					<div>
						<h1 className="text-3xl font-semibold text-slate-900">
							Saved Education <span className="text-[#0069e0]">Plans</span>
						</h1>
						<p className="text-lg mt-1">
							View, manage, and share your saved education plans.
						</p>
					</div>
				</header>

				<div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 space-y-4">
					{error && (
						<div className="bg-rose-50 text-rose-700 border border-rose-100 rounded-lg px-4 py-3">
							{error}
						</div>
					)}

					{/* Plans Summary Table */}
					<div className="overflow-x-auto">
						<table className="min-w-full text-sm table-auto">
							<thead>
								<tr className="text-left text-xs uppercase tracking-wide text-slate-500 border-b border-slate-200 bg-slate-50">
									<th className="px-2 py-3 font-semibold text-center">No.</th>
									<th className="px-2 py-3 font-semibold">Program (Degree)</th>
									<th className="px-2 py-3 font-semibold">Courses</th>
									<th className="px-2 py-3 font-semibold">Total Credits</th>
									<th className="px-2 py-3 font-semibold text-center">
										Actions
									</th>
								</tr>
							</thead>
							<tbody>
								{savedPlans.map((plan, index) => (
									<Fragment key={plan.id}>
										<tr className="border-b border-slate-100 hover:bg-slate-50 transition">
											<td className="px-1 py-3 text-center text-slate-700 font-semibold w">
												{index + 1}
											</td>
											<td className="px-2 py-3 text-slate-700">
												{plan.program}
												{(() => {
													const degree = resolveDegree(plan);
													return degree ? ` (${degree})` : "";
												})()}
											</td>
											<td className="px-2 py-3 text-slate-700">
												<span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-200 text-slate-800">
													{plan.courses.length}
												</span>
											</td>
											<td className="px-2 py-3 text-slate-700">
												<span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
													{getTotalCredits(plan.courses)}
												</span>
											</td>
											<td className="px-2 py-3 text-center">
												<div className="flex items-center justify-center gap-2">
													<button
														type="button"
														className="px-4 py-1.5 rounded-lg bg-emerald-100 text-emerald-700 text-sm font-medium hover:bg-emerald-200 transition"
													>
														Request Advisor Approval
													</button>
													<button
														type="button"
														onClick={() => downloadPlan(plan)}
														className="px-4 py-1.5 rounded-lg bg-emerald-100 hover:bg-emerald-200 transition"
													>
													Download PDF
													</button>
													<button
														type="button"
														onClick={() => toggleExpand(plan.id)}
														className={`px-4 py-1.5 rounded-lg text-sm font-medium transition ${
															expandedPlanId === plan.id
																? "bg-indigo-600 text-white"
																: "bg-indigo-100 text-indigo-700 hover:bg-indigo-200"
														}`}
													>
														{expandedPlanId === plan.id ? "Hide" : "View"}
													</button>
													<button
														type="button"
														onClick={() => handleEdit(plan)}
														className="px-4 py-1.5 rounded-lg bg-orange-200 text-orange-700 text-sm font-medium hover:bg-orange-300 transition"
													>
														Edit
													</button>
													<button
														type="button"
														onClick={() => handleDeletePlan(plan)}
														disabled={deletingPlanId === plan.id}
														className={`px-4 py-1.5 rounded-lg text-sm font-medium transition ${
															deletingPlanId === plan.id
																? "bg-rose-200 text-rose-400 cursor-not-allowed"
																: "bg-rose-100 text-rose-700 hover:bg-rose-200"
														}`}
													>
														{deletingPlanId === plan.id
															? "Deleting..."
															: "Delete"}
													</button>
													
												</div>
											</td>
										</tr>

										{/* Expanded Plan Details */}
										{expandedPlanId === plan.id && (
											<tr key={`${plan.id}-details`}>
												<td colSpan={5} className="p-0">
													<div className="bg-slate-50 border-t border-slate-200 p-6">
														<div className="mb-4 flex items-center justify-between">
															<h3 className="text-lg font-semibold text-slate-800">
																{plan.program} - {plan.university}
															</h3>
															<div className="flex items-center gap-4 text-sm">
																<span className="text-slate-600">
																	Avg. annual cost:{" "}
																	<span className="font-bold text-emerald-700">
																							{findAverageAnnualCost(plan) || "Not reported by College Scorecard"}
																	</span>
																</span>
																<span className="text-slate-600">
																	Total Courses:{" "}
																	<span className="font-bold text-indigo-600">
																		{plan.courses.length}
																	</span>
																</span>
															</div>
														</div>

														<div className="space-y-6">
															{Object.entries(
																groupCoursesByYearAndSemester(plan.courses)
															).map(([year, semesters]) => (
																<div key={year} className="space-y-4">
																	<h4 className="text-md font-semibold text-slate-700 border-b border-slate-200 pb-2">
																		{year}
																	</h4>
																	<div className="grid gap-4 md:grid-cols-2">
																		{Object.entries(semesters).map(
																			([semester, courses]) => (
																				<div
																					key={semester}
																					className="bg-white border border-slate-200 rounded-xl shadow-sm p-4 space-y-3"
																				>
																					<h5 className="text-sm font-semibold text-slate-600 uppercase tracking-wide">
																						{semester}
																					</h5>
																					<ul className="space-y-2 text-sm text-slate-700">
																						{courses.map((course) => (
																							<li
																								key={course.code}
																								className="border border-slate-100 rounded-lg p-3 flex flex-col gap-1 hover:border-indigo-200 hover:bg-indigo-50/50 transition"
																							>
																								<span className="font-semibold text-slate-800">
																									{course.courseName ||
																										course.name}
																								</span>
																								<CourseMeta course={course} />
																							</li>
																						))}
																					</ul>
																				</div>
																			)
																		)}
																	</div>
																</div>
															))}
														</div>
													</div>
												</td>
											</tr>
										)}
									</Fragment>
								))}
								{savedPlans.length === 0 && (
									<tr>
										<td
											colSpan={5}
											className="px-4 py-8 text-center text-slate-500"
										>
											<div className="flex flex-col items-center gap-2">
												<svg
													className="w-12 h-12 text-slate-300"
													fill="none"
													stroke="currentColor"
													viewBox="0 0 24 24"
												>
													<path
														strokeLinecap="round"
														strokeLinejoin="round"
														strokeWidth={1.5}
														d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
													/>
												</svg>
												<span>
													No plans found. Save an education plan to see it here.
												</span>
											</div>
										</td>
									</tr>
								)}
							</tbody>
						</table>
					</div>
				</div>
			</section>
		</>
	);
};

export default ViewEducationPlan;
