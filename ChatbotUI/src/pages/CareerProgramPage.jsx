import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
	FaArrowRight,
	FaBookOpen,
	FaBriefcase,
	FaBuilding,
	FaBuildingColumns,
	FaCode,
	FaCompass,
	FaFlask,
	FaGraduationCap,
	FaHeartPulse,
	FaMagnifyingGlass,
	FaMoneyBillTrendUp,
	FaPalette,
	FaScrewdriverWrench,
	FaXmark,
} from "react-icons/fa6";
import { ACADEMIC_STATS, AREAS_OF_INTEREST } from "../data/academicPrograms.js";
import {
	buildCareerRecords,
	countCareersByArea,
	loadCareerCatalog,
} from "../utils/careerCatalog.js";

const iconByName = {
	briefcase: FaBriefcase,
	building: FaBuildingColumns,
	code: FaCode,
	compass: FaCompass,
	flask: FaFlask,
	graduation: FaGraduationCap,
	heart: FaHeartPulse,
	palette: FaPalette,
	tools: FaScrewdriverWrench,
};

const sectionLabelClass =
	"text-sm font-black uppercase tracking-[0.2em] text-[#c95f22]";

const AcademicsHero = () => (
	<section className="relative isolate flex min-h-[28rem] items-end overflow-hidden bg-[#082a40] text-white sm:min-h-[34rem]">
		<img
			src="/assets/academics-hero.png"
			alt="Graduates celebrating on a Southwestern college campus"
			className="absolute inset-0 -z-20 h-full w-full object-cover object-center"
		/>
		<div aria-hidden="true" className="absolute inset-0 -z-10 bg-gradient-to-r from-[#041b2b]/95 via-[#041b2b]/55 to-transparent" />
		<div aria-hidden="true" className="absolute inset-0 -z-10 bg-gradient-to-t from-black/75 via-transparent to-transparent" />
		<div className="mx-auto w-full max-w-[90rem] px-5 pb-12 pt-28 sm:px-8 sm:pb-16 xl:px-12">
			<h1 className="max-w-4xl text-5xl font-semibold leading-none tracking-tight sm:text-6xl lg:text-7xl">
				Explore academics and careers
			</h1>
			<p className="mt-5 max-w-xl text-lg font-medium leading-8 text-white/85 sm:text-xl">
				Find an academic area that matches your goals, then explore the careers connected to it.
			</p>
		</div>
	</section>
);

const AcademicStats = ({ stats }) => (
	<section id="academic-overview" aria-label="Academic discovery overview" className="scroll-mt-20 bg-white px-5 py-14 sm:px-8 sm:py-20 xl:px-12">
		<div className="mx-auto max-w-6xl">
			<div className="max-w-3xl">
				<p className={sectionLabelClass}>Your future starts here</p>
				<p className="mt-4 text-lg leading-8 text-slate-600">
					Explore programs that match your interests, academic background, and career goals. Compare your options and build a personalized semester-by-semester plan for graduation.
				</p>
			</div>
			<div className="mt-14 grid grid-cols-2 border-y border-slate-200 md:grid-cols-4">
				{stats.map((stat) => (
					<div key={stat.id} className="relative border-b border-r border-slate-200 px-4 py-8 text-center even:border-r-0 md:border-b-0 md:even:border-r md:last:border-r-0">
						<p className="text-4xl font-semibold text-[#073b5c] sm:text-5xl">{stat.value}</p>
						<p className="mt-2 text-sm font-black uppercase tracking-[0.1em] text-slate-600">{stat.label}</p>
						<span aria-hidden="true" className="absolute bottom-0 left-1/2 h-1 w-12 -translate-x-1/2 bg-[#c95f22]" />
					</div>
				))}
			</div>
		</div>
	</section>
);

const AreaOfInterestGrid = ({ areas, careerCounts, careerDataError, activeArea, onSelectArea }) => (
	<section id="areas-of-interest" aria-labelledby="areas-heading" className="scroll-mt-20 bg-[#f7f9fa] px-5 py-16 sm:px-8 sm:py-20 xl:px-12">
		<div className="mx-auto max-w-6xl">
			<div className="max-w-3xl">
				<p className={sectionLabelClass}>Explore careers by academic area</p>
				<h2 id="areas-heading" className="mt-3 text-4xl font-semibold tracking-tight text-[#073b5c] sm:text-5xl">Choose an academic area</h2>
				<p className="mt-4 text-lg leading-8 text-slate-600">
					Start with what motivates you, then explore career options connected to each Northern academic area.
				</p>
			</div>
			<div className="mt-10 grid gap-px overflow-hidden border border-slate-200 bg-slate-200 md:grid-cols-2 xl:grid-cols-3">
				{areas.map((area) => {
					const Icon = iconByName[area.icon] ?? FaBookOpen;
					const selected = activeArea === area.title;
					const careerCount = careerCounts?.[area.title] ?? 0;
					const canExplore = !careerDataError && careerCounts !== null && careerCount > 0;
					return (
						<article
							key={area.id}
							className={`group flex min-h-full flex-col bg-white p-7 transition duration-200 hover:bg-[#f5f9fb] focus-within:bg-[#f5f9fb] ${
								selected ? "relative z-10 ring-2 ring-inset ring-[#c95f22]" : ""
							}`}
						>
							<div className="grid h-14 w-14 place-items-center bg-[#e7f0f5] text-2xl text-[#073b5c] transition group-hover:bg-[#073b5c] group-hover:text-white">
								<Icon aria-hidden="true" />
							</div>
							<h3 className="mt-6 text-2xl font-semibold leading-tight text-[#073b5c]">{area.title}</h3>
							<p className="mt-3 flex-1 leading-7 text-slate-600">{area.description}</p>
							<div className="mt-6 flex items-center justify-between gap-4 border-t border-slate-100 pt-5">
								<span className="text-sm font-bold text-slate-500">
									{careerDataError
										? "Career data unavailable"
										: careerCounts === null
										? "Loading careers..."
										: `${careerCount} ${careerCount === 1 ? "career" : "careers"}`}
								</span>
								<button
									type="button"
									onClick={() => onSelectArea(area.title)}
									aria-pressed={selected}
									disabled={!canExplore}
									className="inline-flex min-h-11 items-center gap-2 px-2 py-2 text-sm font-black uppercase tracking-[0.08em] text-[#c95f22] transition hover:text-[#a94716] focus:outline-none focus-visible:ring-4 focus-visible:ring-orange-200 disabled:cursor-not-allowed disabled:text-slate-400"
								>
									{careerCounts !== null && careerCount === 0 ? "No Careers Listed" : "Explore Careers"}
									{canExplore && <FaArrowRight aria-hidden="true" />}
								</button>
							</div>
						</article>
					);
				})}
			</div>
		</div>
	</section>
);

const META_DESCRIPTION =
	"Explore Northern New Mexico College academic areas and discover connected career paths, skills, and employers.";

const metadata = [
	["name", "description", META_DESCRIPTION],
	["property", "og:title", "Academics and Career Paths | Northern New Mexico College"],
	["property", "og:description", META_DESCRIPTION],
	["name", "twitter:title", "Academics and Career Paths | Northern New Mexico College"],
	["name", "twitter:description", META_DESCRIPTION],
];

const CareerProgramPage = () => {
	const [searchParams, setSearchParams] = useSearchParams();
	const [careers, setCareers] = useState([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");
	const selectedArea = searchParams.get("area") || "";

	useEffect(() => {
		let active = true;
		setLoading(true);
		setError("");
		loadCareerCatalog()
			.then(({ catalog, employers }) => {
				if (!active) return;
				setCareers(buildCareerRecords(catalog, employers));
			})
			.catch((catalogError) => {
				console.error("Unable to load career catalog", catalogError);
				if (!active) return;
				setCareers([]);
				setError("Career data is currently unavailable.");
			})
			.finally(() => {
				if (active) setLoading(false);
			});
		return () => {
			active = false;
		};
	}, []);

	useEffect(() => {
		const previousTitle = document.title;
		const previousMetadata = metadata.map(([attribute, key, content]) => {
			let element = document.head.querySelector(`meta[${attribute}="${key}"]`);
			const created = !element;
			if (!element) {
				element = document.createElement("meta");
				element.setAttribute(attribute, key);
				document.head.appendChild(element);
			}
			const previousContent = element.getAttribute("content");
			element.setAttribute("content", content);
			return { element, created, previousContent };
		});

		document.title = "Academics and Career Paths | Northern New Mexico College";
		return () => {
			document.title = previousTitle;
			previousMetadata.forEach(({ element, created, previousContent }) => {
				if (created) element.remove();
				else if (previousContent === null) element.removeAttribute("content");
				else element.setAttribute("content", previousContent);
			});
		};
	}, []);

	const filteredCareers = useMemo(() => {
		if (!selectedArea) return careers;
		return careers.filter((career) => career.area === selectedArea);
	}, [careers, selectedArea]);
	const careerCounts = useMemo(
		() => (loading ? null : countCareersByArea(careers)),
		[careers, loading]
	);

	const handleAreaChange = useCallback(
		(value) => {
			const next = new URLSearchParams(searchParams);
			next.delete("q");
			if (value) next.set("area", value);
			else next.delete("area");
			setSearchParams(next, { replace: true });
		},
		[searchParams, setSearchParams]
	);

	const scrollToCareerResults = useCallback(() => {
		document.getElementById("career-results-heading")?.scrollIntoView({ behavior: "smooth", block: "start" });
	}, []);

	const handleAreaExplore = useCallback(
		(value) => {
			handleAreaChange(value);
			window.requestAnimationFrame(scrollToCareerResults);
		},
		[handleAreaChange, scrollToCareerResults]
	);

	const clearFilters = useCallback(
		() => setSearchParams({}, { replace: true }),
		[setSearchParams]
	);

	useEffect(() => {
		if (!selectedArea) return undefined;
		const animationFrame = window.requestAnimationFrame(scrollToCareerResults);
		return () => window.cancelAnimationFrame(animationFrame);
	}, [scrollToCareerResults, selectedArea]);

	return (
		<div className="min-h-screen overflow-x-clip bg-[#f7f9fa]">
			<AcademicsHero />
			<AcademicStats stats={ACADEMIC_STATS} />
			<AreaOfInterestGrid
				areas={AREAS_OF_INTEREST}
				careerCounts={careerCounts}
				careerDataError={Boolean(error)}
				activeArea={selectedArea}
				onSelectArea={handleAreaExplore}
			/>
			<section aria-labelledby="career-results-heading" className="px-5 py-14 sm:px-8 sm:py-16 xl:px-12">
				<div className="mx-auto max-w-6xl">
					<div role="group" aria-label="Academic area filter" className="border border-slate-200 bg-white p-4 shadow-sm">
						<div className="flex flex-col gap-3 sm:flex-row sm:items-end">
								<select
									value={selectedArea}
									onChange={(event) => handleAreaChange(event.target.value)}
									className="mt-1.5 h-11 w-full border border-slate-300 bg-white px-3 text-sm font-bold normal-case tracking-normal text-slate-800 outline-none transition focus:border-[#c95f22] focus:ring-4 focus:ring-orange-100"
								>
									<option value="">All academic areas</option>
									{AREAS_OF_INTEREST.map((area) => (
										<option key={area.id} value={area.title}>{area.title}</option>
									))}
								</select>
							<button
								type="button"
								onClick={clearFilters}
								className="inline-flex h-11 items-center justify-center gap-2 border border-slate-300 px-4 text-sm font-black text-slate-700 transition hover:border-[#c95f22] hover:text-[#c95f22] focus:outline-none focus-visible:ring-4 focus-visible:ring-orange-100"
							>
								<FaXmark aria-hidden="true" /> Clear
							</button>
						</div>
					</div>

					<div className="mt-12 flex flex-col gap-3 border-b-4 border-[#c95f22] pb-6 sm:flex-row sm:items-end sm:justify-between">
						<div>
							<p className="text-sm font-black uppercase tracking-[0.2em] text-[#c95f22]">
								{selectedArea || "All academic areas"}
							</p>
							<h2 id="career-results-heading" className="mt-2 text-4xl font-semibold tracking-tight text-[#073b5c] sm:text-5xl">
								Career pathways
							</h2>
						</div>
						<p className="font-black text-slate-900" aria-live="polite">
							{loading ? "Loading careers..." : `${filteredCareers.length} ${filteredCareers.length === 1 ? "career" : "careers"} found`}
						</p>
					</div>

					{error && (
						<div className="mt-8 border border-rose-200 bg-rose-50 px-5 py-4 font-semibold text-rose-700">{error}</div>
					)}

					{!loading && !error && filteredCareers.length > 0 && (
						<div className="mt-8 grid gap-6 xl:grid-cols-2">
							{filteredCareers.map((career) => {
								const pathwayNames = [...new Set(career.pathways.map((pathway) => pathway.program))];
								return (
									<article key={career.id} className="flex h-full flex-col border border-slate-200 border-t-4 border-t-[#073b5c] bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:border-t-[#c95f22] hover:shadow-lg">
										<h3 className="text-2xl font-semibold leading-tight text-[#073b5c]">{career.title}</h3>
										{career.description && <p className="mt-3 leading-7 text-slate-600">{career.description}</p>}

										<div className="mt-6 grid gap-5 border-y border-slate-100 py-5 sm:grid-cols-2">
											<div>
												<p className="flex items-center gap-2 text-sm font-semibold text-slate-600"><FaMoneyBillTrendUp aria-hidden="true" /> Salary range</p>
												<p className="mt-1 font-black text-emerald-700">{career.salary}</p>
											</div>
											<div>
												<p className="text-sm font-black uppercase tracking-wide text-slate-500">Academic pathways</p>
												<div className="mt-2 flex flex-wrap gap-2">
													{pathwayNames.map((pathway) => <span key={pathway} className="bg-[#e7f0f5] px-3 py-1.5 text-sm font-bold text-[#073b5c]">{pathway}</span>)}
												</div>
											</div>
										</div>

										{career.competencies.length > 0 && (
											<div className="mt-5">
												<p className="text-sm font-black uppercase tracking-wide text-slate-500">Key skills</p>
												<ul className="mt-2 flex flex-wrap gap-2">
													{career.competencies.slice(0, 5).map((competency) => <li key={competency.topic} className="border border-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-700">{competency.topic}</li>)}
												</ul>
											</div>
										)}

										{career.employers.length > 0 && (
											<div className="mt-5">
												<p className="flex items-center gap-2 text-sm font-black uppercase tracking-wide text-slate-500"><FaBuilding aria-hidden="true" /> Employers</p>
												<p className="mt-2 leading-7 text-slate-600">{career.employers.slice(0, 5).join(" · ")}</p>
											</div>
										)}
									</article>
								);
							})}
						</div>
					)}

					{!loading && !error && filteredCareers.length === 0 && (
						<div className="mt-8 border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
							<div className="mx-auto grid h-14 w-14 place-items-center bg-slate-100 text-xl text-slate-500"><FaMagnifyingGlass aria-hidden="true" /></div>
							<h3 className="mt-5 text-xl font-black text-slate-950">No careers found</h3>
							<p className="mx-auto mt-2 max-w-lg leading-7 text-slate-600">The current career catalog does not contain a match for these filters.</p>
							<button type="button" onClick={clearFilters} className="mt-6 min-h-11 bg-[#c95f22] px-5 py-2.5 font-black text-white hover:bg-[#a94716] focus:outline-none focus-visible:ring-4 focus-visible:ring-orange-200">Clear Filters</button>
						</div>
					)}
				</div>
			</section>
		</div>
	);
};

export default CareerProgramPage;
