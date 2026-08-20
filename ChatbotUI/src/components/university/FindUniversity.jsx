import { useEffect, useState } from "react";
import { INSTITUTION } from "../../config/institution.js";
import { searchUniversities } from "../../services/universityService.js";
import CollegeDetail from "./CollegeDetail.jsx";

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

const FindUniversity = () => {
	const [college, setCollege] = useState(null);
	const [metricError, setMetricError] = useState("");

	useEffect(() => {
		let cancelled = false;

		const loadNorthern = async () => {
			try {
				const result = await searchUniversities({ search: INSTITUTION.name, perPage: 10 });
				if (cancelled) return;
				setCollege(result.data?.[0] || null);
				setMetricError("");
			} catch {
				if (cancelled) return;
				setMetricError(
					"Official College Scorecard metrics are temporarily unavailable. NNMC links remain available."
				);
			}
		};

		loadNorthern();
		return () => {
			cancelled = true;
		};
	}, []);

	useEffect(() => {
		if (!college || window.location.hash !== "#nnmc-college-details") return undefined;
		const animationFrame = window.requestAnimationFrame(() => {
			document.getElementById("nnmc-college-details")?.scrollIntoView({ behavior: "smooth", block: "start" });
		});
		return () => window.cancelAnimationFrame(animationFrame);
	}, [college]);

	const institution = college || {
		name: INSTITUTION.name,
		city: INSTITUTION.city,
		state: INSTITUTION.state,
		website: INSTITUTION.website,
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
			<article className="relative rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
				<div>
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
						<div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
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
								<p className="text-xs font-semibold uppercase text-slate-500">Average annual Fee</p>
								<p className="font-semibold text-slate-900">
									{formatCurrency(institution.average_annual_cost)}
								</p>
							</div>
							<div className="rounded-lg bg-slate-50 p-3">
								<p className="text-xs font-semibold uppercase text-slate-500">Graduation rate</p>
								<p className="font-semibold text-slate-900">{formatPercent(institution.graduation_rate)}</p>
							</div>
							<div className="rounded-lg bg-slate-50 p-3">
								<p className="text-xs font-semibold uppercase text-slate-500">Median earnings 10 years after entry</p>
								<p className="font-semibold text-slate-900">
									{formatCurrency(institution.median_earnings || institution.typical_earnings)}
								</p>
							</div>
						</div>
					</div>

					<div className="mt-4 flex flex-wrap gap-4 text-sm font-semibold sm:absolute sm:right-6 sm:top-6 sm:mt-0 sm:justify-end">
							<a className="text-blue-700 hover:underline" href={INSTITUTION.academicsUrl} target="_blank" rel="noreferrer">
								Official website
							</a>
							<a className="text-blue-700 hover:underline" href={INSTITUTION.applyUrl} target="_blank" rel="noreferrer">
								Apply to Northern
							</a>
					</div>
				</div>
			</article>

			{college && <CollegeDetail college={college} />}

			<p className="text-xs text-slate-500">
				Institutional metrics shown here come from the U.S. Department of Education College Scorecard; NNMC program data comes from this site&apos;s Northern catalog.
			</p>
		</section>
	);
};

export default FindUniversity;
