import { useEffect } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import {
	FaArrowRight,
	FaBookOpen,
	FaBriefcase,
	FaBuildingColumns,
	FaCode,
	FaComments,
	FaCompass,
	FaFlask,
	FaGraduationCap,
	FaHeartPulse,
	FaPalette,
	FaScrewdriverWrench,
	FaUserGroup,
	FaWallet,
} from "react-icons/fa6";
import {
	ACADEMIC_PROGRAMS,
	ACADEMIC_RESOURCES,
	ACADEMIC_STATS,
	AREAS_OF_INTEREST,
	EDPLAN_STEPS,
} from "../data/academicPrograms.js";

const iconByName = {
	advisor: FaUserGroup,
	briefcase: FaBriefcase,
	building: FaBuildingColumns,
	code: FaCode,
	compass: FaCompass,
	flask: FaFlask,
	graduation: FaGraduationCap,
	heart: FaHeartPulse,
	messages: FaComments,
	palette: FaPalette,
	tools: FaScrewdriverWrench,
	wallet: FaWallet,
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
				Explore by area of interest
			</h1>
			<p className="mt-5 max-w-xl text-lg font-medium leading-8 text-white/85 sm:text-xl">
				Find a program that matches your goals and build a clear path from enrollment to graduation.
			</p>
		</div>
	</section>
);

const AcademicStats = ({ stats }) => (
	<section id="academic-overview" aria-label="Academic discovery overview" className="scroll-mt-20 bg-white px-5 py-14 sm:px-8 sm:py-20 xl:px-12">
		<div >
			<div className="max-w-3xl">
				<p className={sectionLabelClass}>Your future starts here</p>
				<p className="mt-4 text-lg text-slate-600">
					Explore programs that match your interests, academic background, and career goals.Compare your options and build a personalized semester-by-semester plan for graduation.
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

const AreaOfInterestGrid = ({ areas, programCounts, activeArea, onSelectArea }) => (
	<section id="areas-of-interest" aria-labelledby="areas-heading" className="scroll-mt-20">
		<div className="max-w-3xl">
			<p className={sectionLabelClass}>Browse departments and programs</p>
			<p className="mt-4 text-lg leading-8 text-slate-600">
				Still exploring? Start with what motivates you and see the programs connected to each field.
			</p>
		</div>
		<div className="mt-10 grid gap-px overflow-hidden border border-slate-200 bg-slate-200 md:grid-cols-2 xl:grid-cols-3">
			{areas.map((area) => {
				const Icon = iconByName[area.icon] ?? FaBookOpen;
				const selected = activeArea === area.title;
				const programCount = programCounts[area.title] ?? 0;
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
								{programCount} {programCount === 1 ? "program" : "programs"}
							</span>
							<button
								type="button"
								onClick={() => onSelectArea(area.title)}
								aria-pressed={selected}
								className="inline-flex min-h-11 items-center gap-2 px-2 py-2 text-sm font-black uppercase tracking-[0.08em] text-[#c95f22] transition hover:text-[#a94716] focus:outline-none focus-visible:ring-4 focus-visible:ring-orange-200"
							>
								Explore Programs
								<FaArrowRight aria-hidden="true" />
							</button>
						</div>
					</article>
				);
			})}
		</div>
	</section>
);

const EdPlanSteps = ({ steps }) => (
	<section id="planning-process" aria-labelledby="edplan-heading" className="scroll-mt-20 bg-[#073b5c] px-5 py-16 text-white sm:px-8 sm:py-20 xl:px-12">
		<div className="mx-auto max-w-6xl">
			<div className="max-w-2xl">
				<p className="text-sm font-black uppercase tracking-[0.2em] text-orange-200">A clearer way forward</p>
				<h2 id="edplan-heading" className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">
					How EdPlan AI helps
				</h2>
				<p className="mt-4 text-lg leading-8 text-slate-300">
					Move from early exploration to an advisor-ready academic plan in four connected steps.
				</p>
			</div>
			<ol className="mt-10 grid border border-white/15 md:grid-cols-2 xl:grid-cols-4">
				{steps.map((step, index) => (
					<li key={step.id} className="relative border-b border-r border-white/15 bg-white/5 p-7 last:border-r-0 md:[&:nth-child(even)]:border-r-0 xl:border-b-0 xl:[&:nth-child(even)]:border-r xl:last:border-r-0">
						<div className="grid h-11 w-11 place-items-center bg-[#c95f22] text-lg font-black">
							{index + 1}
						</div>
						<h3 className="mt-5 text-xl font-semibold">{step.title}</h3>
						<p className="mt-3 leading-7 text-slate-300">{step.description}</p>
					</li>
				))}
			</ol>
		</div>
	</section>
);

const AcademicResources = ({ resources }) => (
	<section id="student-resources" aria-labelledby="resources-heading" className="scroll-mt-20 px-5 py-16 sm:px-8 sm:py-20 xl:px-12">
		<div className="mx-auto max-w-6xl">
			<div className="max-w-2xl">
				<p className={sectionLabelClass}>Beyond the classroom</p>
				<h2 id="resources-heading" className="mt-3 text-4xl font-semibold tracking-tight text-[#073b5c] sm:text-5xl">
					Support for your whole journey
				</h2>
			</div>
			<div className="mt-10 grid gap-px overflow-hidden border border-slate-200 bg-slate-200 md:grid-cols-2 xl:grid-cols-4">
				{resources.map((resource) => {
					const Icon = iconByName[resource.icon] ?? FaBookOpen;
					return (
						<article key={resource.id} className="flex flex-col bg-white p-7">
							<div className="grid h-12 w-12 place-items-center bg-[#e7f0f5] text-xl text-[#073b5c]">
								<Icon aria-hidden="true" />
							</div>
							<h3 className="mt-5 text-xl font-semibold text-[#073b5c]">{resource.title}</h3>
							<p className="mt-3 flex-1 leading-7 text-slate-600">{resource.description}</p>
							<Link
								to={resource.to}
								className="mt-5 inline-flex min-h-11 items-center gap-2 self-start py-2 text-sm font-black uppercase tracking-[0.08em] text-[#c95f22] underline-offset-4 hover:underline focus:outline-none focus-visible:ring-4 focus-visible:ring-orange-200"
							>
								{resource.cta}
								<FaArrowRight aria-hidden="true" />
							</Link>
						</article>
					);
				})}
			</div>
		</div>
	</section>
);

const META_DESCRIPTION =
	"Discover Northern New Mexico College academic programs and build a personalized semester-by-semester education plan with EdPlan AI.";

const metadata = [
	["name", "description", META_DESCRIPTION],
	["property", "og:title", "Academics | Northern New Mexico College"],
	["property", "og:description", META_DESCRIPTION],
	["name", "twitter:title", "Academics | Northern New Mexico College"],
	["name", "twitter:description", META_DESCRIPTION],
];

const programCounts = ACADEMIC_PROGRAMS.reduce((counts, program) => {
	counts[program.area] = (counts[program.area] ?? 0) + 1;
	return counts;
}, {});

const AcademicsPage = () => {
	const [searchParams] = useSearchParams();
	const navigate = useNavigate();
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

		document.title = "Academics | Northern New Mexico College";
		return () => {
			document.title = previousTitle;
			previousMetadata.forEach(({ element, created, previousContent }) => {
				if (created) element.remove();
				else if (previousContent === null) element.removeAttribute("content");
				else element.setAttribute("content", previousContent);
			});
		};
	}, []);

	const hasLegacyProgramFilters = ["q", "area", "degree"].some((parameter) =>
		searchParams.has(parameter)
	);

	if (hasLegacyProgramFilters) {
		return <Navigate to={`/programs?${searchParams.toString()}`} replace />;
	}

	return (
		<div className="min-h-screen overflow-x-clip bg-white">
			<AcademicsHero />
			<AcademicStats stats={ACADEMIC_STATS} />
			<div className="bg-[#f7f9fa] px-5 py-16 sm:px-8 sm:py-20 xl:px-12">
				<div className="mx-auto max-w-6xl">
					<AreaOfInterestGrid
						areas={AREAS_OF_INTEREST}
						programCounts={programCounts}
						activeArea=""
						onSelectArea={(area) =>
							navigate(`/programs?${new URLSearchParams({ area }).toString()}`)
						}
					/>
				</div>
			</div>
			<EdPlanSteps steps={EDPLAN_STEPS} />
			<AcademicResources resources={ACADEMIC_RESOURCES} />
		</div>
	);
};

export default AcademicsPage;
