import { useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import { INSTITUTION } from "../config/institution.js";
import client from "../services/authService.js";

const US_STATES = [
	"Alabama",
	"Alaska",
	"Arizona",
	"Arkansas",
	"California",
	"Colorado",
	"Connecticut",
	"Delaware",
	"Florida",
	"Georgia",
	"Hawaii",
	"Idaho",
	"Illinois",
	"Indiana",
	"Iowa",
	"Kansas",
	"Kentucky",
	"Louisiana",
	"Maine",
	"Maryland",
	"Massachusetts",
	"Michigan",
	"Minnesota",
	"Mississippi",
	"Missouri",
	"Montana",
	"Nebraska",
	"Nevada",
	"New Hampshire",
	"New Jersey",
	"New Mexico",
	"New York",
	"North Carolina",
	"North Dakota",
	"Ohio",
	"Oklahoma",
	"Oregon",
	"Pennsylvania",
	"Rhode Island",
	"South Carolina",
	"South Dakota",
	"Tennessee",
	"Texas",
	"Utah",
	"Vermont",
	"Virginia",
	"Washington",
	"West Virginia",
	"Wisconsin",
	"Wyoming",
];

const IntakeForm = () => {
	const navigate = useNavigate();
	const [satTaken, setSatTaken] = useState("no");
	const [actTaken, setActTaken] = useState("no");

	const satDisabled = satTaken !== "yes";
	const actDisabled = actTaken !== "yes";

	const handleSubmit = async (event) => {
		event.preventDefault();
		const formData = new FormData(event.target);
		const payload = {};
		for (const [key, value] of formData.entries()) {
			if (payload[key]) {
				payload[key] = Array.isArray(payload[key])
					? [...payload[key], value]
					: [payload[key], value];
			} else {
				payload[key] = value;
			}
		}
		payload.consent = formData.has("consent");

		try {
			await client.post("/intake", payload);
			toast.success("Form saved!");
			navigate("/uni");
		} catch (error) {
			if (error.response?.status === 401) {
				toast.error("Please sign in before saving your academic history.");
				navigate("/login");
				return;
			}
			toast.error(
				"Could not save the form. Review the entered values and try again."
			);
		}
	};

	return (
		<section className="bg-slate-100 min-h-screen flex items-center justify-center p-4">
			<div className="w-full max-w-6xl bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
				<header className="px-6 sm:px-10 py-6 border-b border-slate-200 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white">
					<div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
						<div className="flex flex-col">
							<h1 className="text-xl sm:text-2xl font-semibold">
								For better planning tell us about your academic history
							</h1>
							<p className="text-xs sm:text-sm text-slate-200 mt-1">
								Tell us about your goals so we can tailor your NNMC education plan.
							</p>
						</div>

						<button
							type="button"
							className="px-4 py-2.5 rounded-full border border-slate-300 text-xs sm:text-sm font-medium text-slate-700 bg-white hover:bg-slate-50"
							onClick={() => navigate("/uni")}
						>
							Skip for now
						</button>
					</div>
				</header>

				<form onSubmit={handleSubmit} className="px-6 sm:px-10 py-8 space-y-10">
					{/* Academic Performance */}
					<section>
						<div className="flex items-center justify-between gap-2 mb-4">
							<h2 className="text-lg sm:text-xl font-semibold text-slate-900">
								Academic Performance
							</h2>
							<span className="text-sm font-medium text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-100">
								Required
							</span>
						</div>
						<div className="grid gap-4 md:grid-cols-4">
							<label className="flex flex-col gap-1.5 text-sm font-medium text-slate-700">
								<span className="flex items-center gap-1">
									High School Name <span className="text-red-500">*</span>
								</span>
								<input
									name="high_school_name"
									type="text"
									placeholder="e.g. Lincoln High School"
									className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm shadow-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
									required
								/>
							</label>
							<label className="flex flex-col gap-1.5 text-sm font-medium text-slate-700">
								<span className="flex items-center gap-1">
									Graduation Year <span className="text-red-500">*</span>
								</span>
								<select
									name="graduation_year"
									className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm shadow-sm bg-white focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
									required
								>
									<option value="">Select year</option>
									<option>2025</option>
									<option>2026</option>
									<option>2027</option>
									<option>2028</option>
								</select>
							</label>
							<label className="flex flex-col gap-1.5 text-sm font-medium text-slate-700">
								<span className="flex items-center gap-1">
									State <span className="text-red-500">*</span>
								</span>
								<select
									name="state"
									defaultValue="New Mexico"
									className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm shadow-sm bg-white focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
									required
								>
									{US_STATES.map((state) => (
										<option key={state} value={state}>
											{state}
										</option>
									))}
								</select>
							</label>
							<label className="flex flex-col gap-1.5 text-sm font-medium text-slate-700">
								<span className="flex items-center gap-1">
									Resident Status <span className="text-red-500">*</span>
								</span>
								<select
									name="resident_status"
									className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm shadow-sm bg-white focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
									required
								>
									<option value="">Select status</option>
									<option>In state</option>
									<option>Out of state</option>
									<option>International</option>
								</select>
							</label>
						</div>{" "}
						<div className="mt-6 grid gap-4 md:grid-cols-3">
							<label className="flex flex-col gap-1.5 text-sm font-medium text-slate-700">
								<span className="flex items-center gap-1">
									GPA <span className="text-red-500">*</span>
								</span>
								<input
									name="gpa"
									type="number"
									placeholder="e.g. 3 / 4"
									min="0"
									max="4"
									required
									className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm shadow-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
								/>
								<span className="text-[13px] text-slate-500">
									You can enter GPA as 4 scale
								</span>
							</label>
							<div className="flex flex-col gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-700">
								<span className="font-medium">12th Grade Marksheet</span>
								<span className="text-[13px] text-slate-500">
									Bring this document to your advisor. Online document upload is not available.
								</span>
							</div>
							<label className="flex flex-col gap-1.5 text-sm font-medium text-slate-700">
								Class Rank (if reported)
								<select
									name="class_rank"
									className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm shadow-sm bg-white focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
								>
									<option value="">Not reported</option>
									<option>Top 5%</option>
									<option>Top 10%</option>
									<option>Top 25%</option>
									<option>Top 50%</option>
								</select>
							</label>
							<label className="flex flex-col gap-1.5 text-sm font-medium text-slate-700">
								<span className="flex items-center gap-1">
									Student Type <span className="text-red-500">*</span>
								</span>
								<select
									name="student_type"
									className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm shadow-sm bg-white focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
									required
								>
									<option value="">Select</option>
									<option>First Generation</option>
									<option>African-American</option>
									<option>Hispanic</option>
									<option>Low Income</option>
								</select>
							</label>
						</div>
						<div className="mt-6">
							<div className="flex items-center justify-between mb-2">
								<p className="text-sm font-medium text-slate-700 uppercase tracking-wide">
									Core Subject Grades (recent year)
								</p>
								<p className="text-[13px] text-slate-500">
									Use A/B/C or % as on your transcript.
								</p>
							</div>
							<div className="grid gap-4 md:grid-cols-4">
								{[
									{ name: "grade_english", label: "English" },
									{ name: "grade_math", label: "Mathematics" },
									{ name: "grade_science", label: "Science" },
									{ name: "grade_social_studies", label: "Social Studies" },
								].map((field) => (
									<label
										key={field.name}
										className="flex flex-col gap-1.5 text-sm font-medium text-slate-700"
									>
										<span className="flex items-center gap-1">
											{field.label}
											<span className="text-red-500">*</span>
										</span>
										<input
											name={field.name}
											type="text"
											placeholder="e.g. A / 93%"
											required
											className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm shadow-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
										/>
									</label>
								))}
							</div>
						</div>
					</section>

					{/* Tests */}
					<section className="border-t border-slate-200 pt-6">
						<div className="flex items-center justify-between gap-2 mb-4">
							<h2 className="text-lg sm:text-xl font-semibold text-slate-900">
								Standardized Tests (US)
							</h2>
							<span className="text-sm font-medium text-slate-500">
								Optional but helpful
							</span>
						</div>

						<div className="rounded-xl border border-sky-100 bg-sky-50/60 p-4 sm:p-5 mb-5">
							<div className="flex flex-wrap items-center justify-between gap-3 mb-3">
								<div className="flex items-center gap-2">
									<div className="h-7 w-7 rounded-lg bg-sky-600 text-white flex items-center justify-center text-xs font-semibold">
										SAT
									</div>
									<p className="text-sm font-semibold text-slate-800">
										SAT Scores
									</p>
								</div>
								<div className="flex items-center gap-4 text-xs sm:text-sm text-slate-700">
									<label className="inline-flex items-center gap-1 cursor-pointer">
										<input
											type="radio"
											name="sat_taken"
											value="no"
											checked={satTaken === "no"}
											onChange={() => setSatTaken("no")}
											className="h-4 w-4 text-sky-600 border-slate-300 focus:ring-sky-500"
										/>
										<span>Haven&apos;t taken</span>
									</label>
									<label className="inline-flex items-center gap-1 cursor-pointer">
										<input
											type="radio"
											name="sat_taken"
											value="yes"
											checked={satTaken === "yes"}
											onChange={() => setSatTaken("yes")}
											className="h-4 w-4 text-sky-600 border-slate-300 focus:ring-sky-500"
										/>
										<span>Taken</span>
									</label>
								</div>
							</div>
							<div
								className={`grid gap-4 md:grid-cols-4 ${
									satDisabled ? "opacity-40 pointer-events-none" : ""
								}`}
							>
								{[
									{
										name: "sat_total",
										label: "Total (1600)",
										min: 0,
										max: 1600,
									},
									{ name: "sat_math", label: "Math (800)", min: 0, max: 800 },
									{
										name: "sat_reading",
										label: "Reading & Writing (800)",
										min: 0,
										max: 800,
									},
								].map((field) => (
									<label
										key={field.name}
										className="flex flex-col gap-1.5 text-xs font-medium text-slate-700"
									>
										{field.label}
										<input
											name={field.name}
											type="number"
											min={field.min}
											max={field.max}
											placeholder="e.g. 400"
											disabled={satDisabled}
											className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:ring-2 focus:ring-sky-500 focus:border-sky-500 outline-none"
										/>
									</label>
								))}
								<label className="flex flex-col gap-1.5 text-xs font-medium text-slate-700">
									Test Date
									<input
										name="sat_date"
										type="date"
										disabled={satDisabled}
										className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:ring-2 focus:ring-sky-500 focus:border-sky-500 outline-none"
									/>
								</label>
							</div>
						</div>

						<div className="rounded-xl border border-emerald-100 bg-emerald-50/60 p-4 sm:p-5">
							<div className="flex flex-wrap items-center justify-between gap-3 mb-3">
								<div className="flex items-center gap-2">
									<div className="h-7 w-7 rounded-lg bg-emerald-600 text-white flex items-center justify-center text-xs font-semibold">
										ACT
									</div>
									<p className="text-sm font-semibold text-slate-800">
										ACT Scores
									</p>
								</div>
								<div className="flex items-center gap-4 text-xs sm:text-sm text-slate-700">
									<label className="inline-flex items-center gap-1 cursor-pointer">
										<input
											type="radio"
											name="act_taken"
											value="no"
											checked={actTaken === "no"}
											onChange={() => setActTaken("no")}
											className="h-4 w-4 text-emerald-600 border-slate-300 focus:ring-emerald-500"
										/>
										<span>Haven&apos;t taken</span>
									</label>
									<label className="inline-flex items-center gap-1 cursor-pointer">
										<input
											type="radio"
											name="act_taken"
											value="yes"
											checked={actTaken === "yes"}
											onChange={() => setActTaken("yes")}
											className="h-4 w-4 text-emerald-600 border-slate-300 focus:ring-emerald-500"
										/>
										<span>Taken</span>
									</label>
								</div>
							</div>
							<div
								className={`grid gap-4 md:grid-cols-6 ${
									actDisabled ? "opacity-40 pointer-events-none" : ""
								}`}
							>
								{[
									{ name: "act_composite", label: "Composite (36)" },
									{ name: "act_english", label: "English" },
									{ name: "act_math", label: "Math" },
									{ name: "act_reading", label: "Reading" },
									{ name: "act_science", label: "Science" },
								].map((field) => (
									<label
										key={field.name}
										className="flex flex-col gap-1.5 text-xs font-medium text-slate-700"
									>
										{field.label}
										<input
											name={field.name}
											type="number"
											min="1"
											max="36"
											placeholder="e.g. 30"
											disabled={actDisabled}
											className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
										/>
									</label>
								))}
								<label className="flex flex-col gap-1.5 text-xs font-medium text-slate-700">
									Test Date
									<input
										name="act_date"
										type="date"
										disabled={actDisabled}
										className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
									/>
								</label>
							</div>
						</div>
					</section>

					{/* Financial */}
					<section className="border-t border-slate-200 pt-6">
						<div className="flex items-center justify-between gap-2 mb-4">
							<h2 className="text-lg sm:text-xl font-semibold text-slate-900">
								Financial Readiness for NNMC
							</h2>
							<span className="text-xs font-medium text-amber-700 bg-amber-50 px-2.5 py-1 rounded-full border border-amber-100">
								Used to plan a realistic NNMC pathway
							</span>
						</div>

						<p className="text-sm sm:text-[14px] font-semibold text-slate-600 mb-4">
							These details help compare your available resources with Northern New
							Mexico College tuition and living costs. International applicants
							should also review NNMC&apos;s current admissions requirements.
						</p>

						<div className="grid gap-4 md:grid-cols-2">
							<label className="flex flex-col gap-1.5 text-sm font-medium text-slate-700">
								<span className="flex items-center gap-1">
									Estimated Total Budget (USD per year){" "}
									<span className="text-red-500">*</span>
								</span>
								<div className="relative">
									<span className="absolute inset-y-0 left-3 flex items-center text-xs text-slate-500">
										$
									</span>
									<input
										name="budget_total"
										type="number"
										min="0"
										required
										placeholder="e.g. 35000"
										className="w-full rounded-lg border border-slate-300 pl-7 pr-3 py-2.5 text-sm shadow-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
									/>
								</div>
								<span className="text-[13px] text-slate-500">
									Include tuition, housing, food, insurance, and other living
									costs.
								</span>
							</label>
							<label className="flex flex-col gap-1.5 text-sm font-medium text-slate-700">
								<span className="flex items-center gap-1">
									Maximum Tuition You Can Afford (USD per year){" "}
									<span className="text-red-500">*</span>
								</span>
								<div className="relative">
									<span className="absolute inset-y-0 left-3 flex items-center text-xs text-slate-500">
										$
									</span>
									<input
										name="max_tuition"
										type="number"
										min="0"
										placeholder="e.g. 22000"
										required
										className="w-full rounded-lg border border-slate-300 pl-7 pr-3 py-2.5 text-sm shadow-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
									/>
								</div>
								<span className="text-[13px] text-slate-500">
								Helps you assess an affordable NNMC plan.
								</span>
							</label>
						</div>

						<div className="mt-5">
							<p className="block text-sm font-medium text-slate-700 mb-2">
								Will you need financial aid or scholarships?
							</p>
							<div className="flex flex-wrap gap-3 text-sm sm:text-sm text-slate-700">
								{[
									{ value: "no_aid", label: "No, I can attend without aid" },
									{ value: "some_aid", label: "Yes, I will need some aid" },
									{
										value: "significant_aid",
										label: "Yes, I will need significant aid",
									},
								].map((option) => (
									<label
										key={option.value}
										className="inline-flex items-center gap-2 cursor-pointer"
									>
										<input
											type="radio"
											name="need_aid"
											value={option.value}
											className="h-4 w-4 text-emerald-600 border-slate-300 focus:ring-emerald-500"
										/>
										<span>{option.label}</span>
									</label>
								))}
							</div>
						</div>

						<div className="mt-5">
							<p className="block text-sm font-medium text-slate-700 mb-2">
								Main ways you expect to pay for college (select all that apply)
							</p>
							<div className="flex flex-wrap gap-2">
								{[
									"Family savings / income",
									"Student loans",
									"Need-based aid",
									"Merit scholarships",
									"Sponsor (relative/company)",
									"Other",
								].map((label) => (
									<label
										key={label}
										className="inline-flex items-center gap-2 rounded-full border border-slate-300 px-3 py-1.5 text-sm cursor-pointer hover:border-emerald-500 hover:bg-emerald-50"
									>
										<input
											type="checkbox"
											name="pay_options"
											value={label}
											className="h-4 w-4 text-emerald-600 border-slate-300 rounded focus:ring-emerald-500"
										/>
										<span>{label}</span>
									</label>
								))}
							</div>
						</div>

						<div className="mt-5">
							<p className="block text-sm font-medium text-slate-700 mb-2">
								Are you interested in on-campus work (if eligible)?
							</p>
							<div className="flex flex-wrap gap-4 text-xs sm:text-sm text-slate-700">
								{["yes", "no"].map((value) => (
									<label
										key={value}
										className="inline-flex items-center gap-2 cursor-pointer"
									>
										<input
											type="radio"
											name="work_study"
											value={value}
											className="h-4 w-4 text-emerald-600 border-slate-300 focus:ring-emerald-500"
										/>
										<span>{value === "yes" ? "Yes" : "No"}</span>
									</label>
								))}
							</div>
						</div>
					</section>

					<section className="border-t border-slate-200 pt-6 mt-2">
						<label className="flex items-start gap-2 text-xs sm:text-sm text-slate-700 mb-4">
							<input
								name="consent"
								type="checkbox"
								value="true"
								required
								className="mt-0.5 h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
							/>
							<span>
								I confirm that the information provided is accurate to the best
								of my knowledge. This site will use it only to help build my
								{INSTITUTION.shortName} education pathway.
							</span>
						</label>

						<div className="flex gap-3 justify-end">
							<button
								type="button"
								className="px-4 py-2.5 rounded-full border border-slate-300 text-xs sm:text-sm font-medium text-slate-700 bg-white hover:bg-slate-50"
								onClick={() => navigate("/uni")}
							>
								Skip for now
							</button>
							<button
								type="submit"
								className="px-5 py-2.5 rounded-full text-xs sm:text-sm font-semibold text-white bg-gradient-to-r from-sky-600 to-emerald-600 shadow-md hover:shadow-lg hover:brightness-105"
							>
								Submit
							</button>
						</div>
					</section>
				</form>
			</div>
		</section>
	);
};

export default IntakeForm;
