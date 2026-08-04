import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { INSTITUTION } from "../../config/institution.js";
import { listPrograms } from "../../services/educationPlanService.js";
import { searchUniversities } from "../../services/universityService.js";
import { save as saveStorage } from "../../utils/storage.js";

const hasValue = (value) =>
	value !== undefined && value !== null && value !== "";

const formatPercent = (value) =>
	hasValue(value)
		? `${(Number(value) * 100).toFixed(1).replace(/\.0$/, "")}%`
		: "Not reported by College Scorecard";

const formatCurrency = (value) =>
	hasValue(value)
		? `$${Number(value).toLocaleString()}`
		: "Not reported by College Scorecard";

const formatAdmission = (college) => {
	if (hasValue(college?.acceptance_rate)) {
		return formatPercent(college.acceptance_rate);
	}
	if (college?.open_admissions_policy === true) {
		return "Open Admission Policy";
	}
	return "Not reported by College Scorecard";
};

const normalizeDegree = (value = "") => {
	const normalized = String(value).trim().toLowerCase();
	if (normalized.includes("certificate")) return "Certificate";
	if (normalized.includes("associate")) return "Associate";
	if (normalized.includes("bachelor")) return "Bachelor's";
	if (normalized.includes("master")) return "Master's";
	return value || "Degree not specified";
};

const FindUniversity = () => {
	const navigate = useNavigate();
	const [college, setCollege] = useState(null);
	const [programs, setPrograms] = useState([]);
	const [selectedProgramId, setSelectedProgramId] = useState("");
	const [loading, setLoading] = useState(true);
	const [metricError, setMetricError] = useState("");
	const [catalogError, setCatalogError] = useState("");

	useEffect(() => {
		let cancelled = false;

		const loadNorthern = async () => {
			setLoading(true);
			const [collegeResult, programResult] = await Promise.allSettled([
				searchUniversities({ search: INSTITUTION.name, perPage: 10 }),
				listPrograms(),
			]);
			if (cancelled) return;

			if (collegeResult.status === "fulfilled") {
				setCollege(collegeResult.value.data?.[0] || null);
				setMetricError("");
			} else {
				console.error("Unable to load NNMC College Scorecard data", collegeResult.reason);
				setMetricError(
					"Official College Scorecard metrics are temporarily unavailable. NNMC links and program planning remain available."
				);
			}

			if (programResult.status === "fulfilled") {
				setPrograms(programResult.value);
				setCatalogError("");
			} else {
				console.error("Unable to load NNMC programs", programResult.reason);
				setCatalogError("The NNMC program catalog is temporarily unavailable.");
			}
			setLoading(false);
		};

		loadNorthern();
		return () => {
			cancelled = true;
		};
	}, []);

	const selectedProgram = useMemo(
		() => programs.find((program) => program.program_id === selectedProgramId),
		[programs, selectedProgramId]
	);

	const institution = college || {
		name: INSTITUTION.name,
		city: INSTITUTION.city,
		state: INSTITUTION.state,
		website: INSTITUTION.website,
	};

	const saveSelection = () => {
		saveStorage("University", INSTITUTION.name);
		saveStorage("UniversityUnitId", college?.unit_id || "");
		saveStorage("UniversityState", INSTITUTION.state);
		saveStorage("universityview", INSTITUTION.name);
		if (selectedProgram) {
			saveStorage("Programname", selectedProgram.program);
			saveStorage("Programnameview", selectedProgram.program);
			saveStorage("SelectedProgram", selectedProgram.program);
			saveStorage("ProgramDegree", selectedProgram.degree || "");
			saveStorage("SelectedDegreeLevel", selectedProgram.degree || "");
		}
	};

	const viewDetails = () => {
		if (!college?.unit_id) return;
		saveStorage("LastCollegeDetail", college);
		navigate(`/college/${college.unit_id}`, { state: { college } });
	};

	const buildPlan = () => {
		saveSelection();
		navigate("/educationplan");
	};

	return (
		<section className="space-y-6">
			<header className="rounded-2xl bg-gradient-to-r from-slate-950 via-slate-900 to-blue-950 p-6 text-white shadow-lg">
				<div className="flex flex-col gap-5 md:flex-row md:items-center">
					<img
						src={INSTITUTION.logoUrl}
						alt="Northern New Mexico College"
						className="h-20 w-auto rounded-lg bg-white p-2"
					/>
					<div>
						<p className="text-sm font-semibold uppercase tracking-[0.18em] text-sky-300">
							NNMC Student Planning Hub
						</p>
						<h1 className="mt-1 text-3xl font-bold md:text-4xl">
							Northern New Mexico College
						</h1>
						<p className="mt-2 max-w-2xl text-slate-200">
							Explore Northern&apos;s academic programs, review official federal
							college data.
						</p>
					</div>
				</div>
			</header>

			{metricError && (
				<div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
					{metricError}
				</div>
			)}
			{catalogError && (
				<div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
					{catalogError}
				</div>
			)}

			<article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
				<div className="flex flex-col gap-6 lg:flex-row lg:justify-between">
					<div className="space-y-3">
						<div>
							<h2 className="text-2xl font-bold text-slate-900">{institution.name}</h2>
							<p className="text-slate-600">
								{institution.city}, {institution.state}
								{institution.organization_type
									? ` · ${institution.organization_type}`
									: ""}
							</p>
						</div>
						<div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
							<div className="rounded-lg bg-slate-50 p-3">
								<p className="text-xs font-semibold uppercase text-slate-500">Enrollment</p>
								<p className="font-semibold text-slate-900">
									{hasValue(institution.size)
										? Number(institution.size).toLocaleString()
										: "Not reported by College Scorecard"}
								</p>
							</div>
							<div className="rounded-lg bg-slate-50 p-3">
								<p className="text-xs font-semibold uppercase text-slate-500">Admission</p>
								<p className="font-semibold text-slate-900">{formatAdmission(institution)}</p>
							</div>
							<div className="rounded-lg bg-slate-50 p-3">
								<p className="text-xs font-semibold uppercase text-slate-500">Average annual net Fee</p>
								<p className="font-semibold text-slate-900">
									{formatCurrency(institution.average_annual_cost)}
								</p>
							</div>
							<div className="rounded-lg bg-slate-50 p-3">
								<p className="text-xs font-semibold uppercase text-slate-500">Graduation rate</p>
								<p className="font-semibold text-slate-900">{formatPercent(institution.graduation_rate)}</p>
							</div>
							<div className="rounded-lg bg-slate-50 p-3 sm:col-span-2">
								<p className="text-xs font-semibold uppercase text-slate-500">Median earnings 10 years after entry</p>
								<p className="font-semibold text-slate-900">
									{formatCurrency(institution.median_earnings || institution.typical_earnings)}
								</p>
							</div>
						</div>
					</div>

					<div className="min-w-full space-y-3 lg:min-w-80">
						<label className="block text-sm font-semibold text-slate-700" htmlFor="nnmc-program">
							Choose an NNMC program
						</label>
						<select
							id="nnmc-program"
							value={selectedProgramId}
							onChange={(event) => setSelectedProgramId(event.target.value)}
							className="w-full rounded-lg border border-slate-300 px-3 py-2.5"
							disabled={loading || programs.length === 0}
						>
							<option value="">Select a program</option>
							{programs.map((program) => (
								<option key={program.program_id} value={program.program_id}>
									{program.program} ({normalizeDegree(program.degree)})
								</option>
							))}
						</select>
						<div className="flex flex-wrap gap-2">
							<button
								type="button"
								onClick={buildPlan}
								disabled={!selectedProgram}
								className="rounded-lg bg-[#0069e0] px-4 py-2 font-semibold text-white hover:bg-[#1977e3] disabled:cursor-not-allowed disabled:opacity-50"
							>
								Create Education Plan
							</button>
							<button
								type="button"
								onClick={viewDetails}
								disabled={!college?.unit_id}
								className="rounded-lg border border-slate-300 px-4 py-2 font-semibold text-slate-700 hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-50"
							>
								View College Details
							</button>
						</div>
						<div className="flex flex-wrap gap-4 text-sm font-semibold">
							<a className="text-blue-700 hover:underline" href={INSTITUTION.academicsUrl} target="_blank" rel="noreferrer">
								Official academics
							</a>
							<a className="text-blue-700 hover:underline" href={INSTITUTION.applyUrl} target="_blank" rel="noreferrer">
								Apply to Northern
							</a>
						</div>
					</div>
				</div>
			</article>

			<p className="text-xs text-slate-500">
				Institutional metrics shown here come from the U.S. Department of Education College Scorecard; NNMC program data comes from this site&apos;s Northern catalog.
			</p>
		</section>
	);
};

export default FindUniversity;
