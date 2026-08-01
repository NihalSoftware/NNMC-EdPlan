import { Link } from "react-router-dom";
import {
	FaArrowRight,
	FaBookOpen,
	FaBriefcase,
	FaBuildingColumns,
	FaChartLine,
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
	"text-sm font-black uppercase tracking-[0.18em] text-indigo-700";

export const AcademicsHero = () => (
	<section className="relative overflow-hidden bg-slate-950 text-white">
		<div
			aria-hidden="true"
			className="absolute -right-24 -top-28 h-96 w-96 rounded-full bg-indigo-500/20 blur-3xl"
		/>
		<div
			aria-hidden="true"
			className="absolute -bottom-48 left-1/4 h-96 w-96 rounded-full bg-sky-400/10 blur-3xl"
		/>
		<div className="relative mx-auto grid max-w-7xl gap-12 px-5 py-16 sm:px-8 sm:py-20 xl:grid-cols-[1.2fr_0.8fr] xl:items-center xl:px-12 xl:py-24">
			<div className="max-w-3xl">
				<p className="mb-5 inline-flex items-center gap-2 rounded-full border border-indigo-300/20 bg-indigo-300/10 px-4 py-2 text-sm font-bold text-indigo-100">
					<FaGraduationCap aria-hidden="true" />
					EdPlan AI Program Discovery
				</p>
				<h1 className="text-4xl font-black leading-[1.08] tracking-tight sm:text-5xl xl:text-6xl">
					Explore Colleges, Programs and Career Paths
				</h1>
				<p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300 sm:text-xl">
					Discover programs that match your interests, compare academic options,
					understand requirements, and build a clear path from enrollment to graduation.
				</p>
				<div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
					<a
						href="#program-explorer"
						className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-indigo-500 px-6 py-3 font-bold text-white shadow-lg shadow-indigo-950/30 transition hover:bg-indigo-400 focus:outline-none focus-visible:ring-4 focus-visible:ring-indigo-300/50"
					>
						Explore Programs
						<FaArrowRight aria-hidden="true" />
					</a>
					<Link
						to="/educationplan"
						className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl border border-slate-600 bg-white/5 px-6 py-3 font-bold text-white transition hover:border-slate-400 hover:bg-white/10 focus:outline-none focus-visible:ring-4 focus-visible:ring-slate-300/40"
					>
						<FaBookOpen aria-hidden="true" />
						Build My Education Plan
					</Link>
					<Link
						to="/intake"
						className="inline-flex min-h-12 items-center justify-center px-4 py-3 font-bold text-indigo-200 underline-offset-4 hover:text-white hover:underline focus:outline-none focus-visible:ring-4 focus-visible:ring-indigo-300/40"
					>
						Talk to an Advisor
					</Link>
				</div>
			</div>

			<div
				aria-hidden="true"
				className="relative mx-auto hidden w-full max-w-md xl:block"
			>
				<div className="absolute -inset-3 rotate-3 rounded-[2rem] bg-gradient-to-br from-indigo-500/30 to-sky-400/10" />
				<div className="relative rounded-[1.75rem] border border-white/10 bg-slate-900/90 p-6 shadow-2xl backdrop-blur">
					<div className="flex items-center justify-between">
						<div>
							<p className="text-xs font-black uppercase tracking-[0.18em] text-indigo-300">
								Your path
							</p>
							<p className="mt-1 text-xl font-black">Program match overview</p>
						</div>
						<div className="grid h-12 w-12 place-items-center rounded-2xl bg-indigo-500 text-xl">
							<FaChartLine />
						</div>
					</div>
					<div className="mt-7 space-y-3">
						{[
							["Discover", "Programs aligned to your goals", "bg-indigo-500"],
							["Compare", "Requirements, format and careers", "bg-sky-400"],
							["Plan", "A semester-by-semester pathway", "bg-emerald-400"],
						].map(([label, detail, color], index) => (
							<div
								key={label}
								className="flex items-center gap-4 rounded-2xl border border-white/10 bg-white/5 p-4"
							>
								<div className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl ${color} font-black text-slate-950`}>
									{index + 1}
								</div>
								<div>
									<p className="font-black">{label}</p>
									<p className="text-sm text-slate-400">{detail}</p>
								</div>
							</div>
						))}
					</div>
				</div>
			</div>
		</div>
	</section>
);

export const AcademicStats = ({ stats }) => (
	<section aria-label="Academic discovery overview" className="relative z-10 -mt-7 px-5 sm:px-8 xl:px-12">
		<div className="mx-auto grid max-w-7xl grid-cols-2 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-900/5 lg:grid-cols-4">
			{stats.map((stat) => (
				<div
					key={stat.id}
					className="border-b border-r border-slate-200 p-5 last:border-r-0 sm:p-6 lg:border-b-0"
				>
					<p className="text-2xl font-black text-slate-950 sm:text-3xl">{stat.value}</p>
					<p className="mt-1 text-sm font-semibold text-slate-500">{stat.label}</p>
				</div>
			))}
		</div>
	</section>
);

export const AreaOfInterestGrid = ({ areas, programCounts, activeArea, onSelectArea }) => (
	<section aria-labelledby="areas-heading" className="mt-16">
		<div className="max-w-2xl">
			<p className={sectionLabelClass}>Find your direction</p>
			<h2 id="areas-heading" className="mt-3 text-3xl font-black tracking-tight text-slate-950 sm:text-4xl">
				Explore by area of interest
			</h2>
			<p className="mt-4 text-lg leading-8 text-slate-600">
				Start with what motivates you. Each area opens a focused set of program options below.
			</p>
		</div>
		<div className="mt-8 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
			{areas.map((area) => {
				const Icon = iconByName[area.icon] ?? FaBookOpen;
				const selected = activeArea === area.title;
				const programCount = programCounts[area.title] ?? 0;
				return (
					<article
						key={area.id}
						className={`group flex min-h-full flex-col rounded-2xl border bg-white p-6 shadow-sm transition duration-200 hover:-translate-y-1 hover:shadow-lg focus-within:-translate-y-1 focus-within:shadow-lg ${
							selected ? "border-indigo-400 ring-4 ring-indigo-100" : "border-slate-200"
						}`}
					>
						<div className="grid h-12 w-12 place-items-center rounded-2xl bg-indigo-50 text-xl text-indigo-700 transition group-hover:bg-indigo-600 group-hover:text-white">
							<Icon aria-hidden="true" />
						</div>
						<h3 className="mt-5 text-xl font-black text-slate-950">{area.title}</h3>
						<p className="mt-3 flex-1 leading-7 text-slate-600">{area.description}</p>
						<div className="mt-6 flex items-center justify-between gap-4 border-t border-slate-100 pt-5">
							<span className="text-sm font-bold text-slate-500">
								{programCount} demo {programCount === 1 ? "program" : "programs"}
							</span>
							<button
								type="button"
								onClick={() => onSelectArea(area.title)}
								aria-pressed={selected}
								className="inline-flex min-h-11 items-center gap-2 rounded-lg px-3 py-2 text-sm font-black text-indigo-700 transition hover:bg-indigo-50 focus:outline-none focus-visible:ring-4 focus-visible:ring-indigo-200"
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

export const EdPlanSteps = ({ steps }) => (
	<section aria-labelledby="edplan-heading" className="bg-slate-950 px-5 py-16 text-white sm:px-8 sm:py-20 xl:px-12">
		<div className="mx-auto max-w-7xl">
			<div className="max-w-2xl">
				<p className="text-sm font-black uppercase tracking-[0.18em] text-indigo-300">A clearer way forward</p>
				<h2 id="edplan-heading" className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">
					How EdPlan AI helps
				</h2>
				<p className="mt-4 text-lg leading-8 text-slate-300">
					Move from early exploration to an advisor-ready academic plan in four connected steps.
				</p>
			</div>
			<ol className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
				{steps.map((step, index) => (
					<li key={step.id} className="relative rounded-2xl border border-white/10 bg-white/5 p-6">
						<div className="grid h-10 w-10 place-items-center rounded-xl bg-indigo-500 font-black">
							{index + 1}
						</div>
						<h3 className="mt-5 text-xl font-black">{step.title}</h3>
						<p className="mt-3 leading-7 text-slate-300">{step.description}</p>
					</li>
				))}
			</ol>
		</div>
	</section>
);

export const AcademicResources = ({ resources }) => (
	<section aria-labelledby="resources-heading" className="px-5 py-16 sm:px-8 sm:py-20 xl:px-12">
		<div className="mx-auto max-w-7xl">
			<div className="max-w-2xl">
				<p className={sectionLabelClass}>Support for the whole journey</p>
				<h2 id="resources-heading" className="mt-3 text-3xl font-black tracking-tight text-slate-950 sm:text-4xl">
					Academic support resources
				</h2>
			</div>
			<div className="mt-8 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
				{resources.map((resource) => {
					const Icon = iconByName[resource.icon] ?? FaBookOpen;
					return (
						<article key={resource.id} className="flex flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
							<div className="grid h-11 w-11 place-items-center rounded-xl bg-sky-50 text-lg text-sky-700">
								<Icon aria-hidden="true" />
							</div>
							<h3 className="mt-5 text-lg font-black text-slate-950">{resource.title}</h3>
							<p className="mt-3 flex-1 leading-7 text-slate-600">{resource.description}</p>
							<Link
								to={resource.to}
								className="mt-5 inline-flex min-h-11 items-center gap-2 self-start rounded-lg py-2 font-black text-indigo-700 underline-offset-4 hover:underline focus:outline-none focus-visible:ring-4 focus-visible:ring-indigo-200"
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

export const InstitutionalCTA = () => (
	<section aria-labelledby="institution-cta-heading" className="px-5 pb-20 sm:px-8 xl:px-12">
		<div className="mx-auto max-w-7xl overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-700 to-slate-950 px-6 py-12 text-white shadow-2xl sm:px-10 lg:flex lg:items-center lg:justify-between lg:gap-12 lg:px-12">
			<div className="max-w-3xl">
				<p className="text-sm font-black uppercase tracking-[0.18em] text-indigo-200">For colleges and universities</p>
				<h2 id="institution-cta-heading" className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">
					Bring Intelligent Program Discovery to Your Institution
				</h2>
				<p className="mt-5 text-lg leading-8 text-indigo-100">
					Help prospective and current students explore programs, compare options, understand requirements,
					and create personalized education plans using StudentSpace.ai and EdPlan AI.
				</p>
			</div>
			<div className="mt-8 flex shrink-0 flex-col gap-3 sm:flex-row lg:mt-0 lg:flex-col">
				<Link
					to="/intake"
					className="inline-flex min-h-12 items-center justify-center rounded-xl bg-white px-6 py-3 font-black text-indigo-800 transition hover:bg-indigo-50 focus:outline-none focus-visible:ring-4 focus-visible:ring-white/40"
				>
					Book a Demo
				</Link>
				<Link
					to="/educationplan"
					className="inline-flex min-h-12 items-center justify-center rounded-xl border border-indigo-300/50 px-6 py-3 font-black text-white transition hover:bg-white/10 focus:outline-none focus-visible:ring-4 focus-visible:ring-white/30"
				>
					Learn About EdPlan AI
				</Link>
			</div>
		</div>
	</section>
);
