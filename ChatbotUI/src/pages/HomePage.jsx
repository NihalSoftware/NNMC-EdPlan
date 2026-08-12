import { Link } from "react-router-dom";
import {
	FaArrowRight,
	FaBookOpen,
	FaChartLine,
	FaComments,
	FaCompass,
	FaGraduationCap,
	FaMagnifyingGlass,
	FaRocket,
	FaRoute,
	FaUserGroup,
	FaWallet,
} from "react-icons/fa6";
import { load } from "../utils/storage.js";
import {
	ACADEMIC_RESOURCES,
	EDPLAN_STEPS,
} from "../data/academicPrograms.js";

const resourceIconByName = {
	advisor: FaUserGroup,
	compass: FaCompass,
	messages: FaComments,
	wallet: FaWallet,
};

const sectionLabelClass =
	"text-sm font-black uppercase tracking-[0.2em] text-[#c95f22]";

const homepageFeatures = [
	{
		id: "explore",
		title: "Explore Options",
		description: "Discover Northern programs built around your goals.",
		icon: FaCompass,
	},
	{
		id: "plan",
		title: "Plan Your Path",
		description: "Build a semester-by-semester plan that works for you.",
		icon: FaRoute,
	},
	{
		id: "progress",
		title: "Track Progress",
		description: "Stay on track and adjust your plan as you grow.",
		icon: FaChartLine,
	},
	{
		id: "prepare",
		title: "Meet Prepared",
		description: "Walk into advising with a clear path and confidence.",
		icon: FaComments,
	},
];

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
					const Icon = resourceIconByName[resource.icon] ?? FaBookOpen;
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

const HomePage = () => {
	const profile = load("UserProfile");
	const firstName =
		typeof profile?.first_name === "string"
			? profile.first_name
			: typeof profile?.firstName === "string"
			? profile.firstName
			: "";

	return (
		<div className="min-h-screen overflow-x-clip bg-white">
			<section className="relative isolate overflow-hidden bg-[#f8fbff] px-5 pb-12 pt-14 sm:px-8 sm:pb-16 sm:pt-16 xl:px-12 xl:pt-12">
				<img
					src="/assets/home-hero-landscape.svg"
					alt=""
					aria-hidden="true"
					className="pointer-events-none absolute inset-x-0 bottom-0 -z-10 h-[68%] w-full object-cover object-bottom"
				/>
				<div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-20 bg-[radial-gradient(circle_at_50%_12%,rgba(219,234,254,0.6),transparent_36%)]" />

				<div className="mx-auto flex min-h-[46rem] max-w-6xl flex-col items-center text-center">
					<div className="inline-flex min-h-11 items-center gap-2 rounded-full bg-blue-100/80 px-5 py-2 text-sm font-bold text-blue-700 ring-1 ring-inset ring-blue-200/60 backdrop-blur-sm">
						<FaGraduationCap aria-hidden="true" className="text-base" />
						{firstName ? `Welcome back, ${firstName}` : "For Students in New Mexico"}
					</div>

					<h1 className="mt-8 max-w-4xl text-5xl font-black leading-[0.98] tracking-[-0.045em] text-[#071a38] sm:text-6xl lg:text-[5.25rem]">
						<span className="block">Your Education.</span>
						<span className="mt-2 block">Your Future.</span>
						<span className="mt-2 block bg-gradient-to-r from-[#1857d9] to-[#3278ee] bg-clip-text text-transparent">Your Plan.</span>
					</h1>

					<p className="mt-7 max-w-2xl text-lg font-medium leading-8 text-slate-600 sm:text-xl">
						Explore Northern programs, discover the right path, and create your personalized education plan
						<span className="font-bold text-[#1857d9]"> before </span>
						you meet with your advisor.
					</p>

					<div className="mt-8 flex w-full flex-col items-stretch justify-center gap-4 sm:w-auto sm:flex-row sm:items-center">
						<Link
							to="/educationplan"
							className="inline-flex min-h-14 items-center justify-center gap-3 rounded-xl bg-[#1759df] px-7 py-3 text-base font-extrabold text-white shadow-[0_14px_30px_-12px_rgba(23,89,223,0.8)] transition hover:-translate-y-0.5 hover:bg-[#0e47c4] focus:outline-none focus-visible:ring-4 focus-visible:ring-blue-200"
						>
							<FaRocket aria-hidden="true" />
							Start My Education Plan
						</Link>
						<Link
							to="/programs"
							className="inline-flex min-h-14 items-center justify-center gap-3 rounded-xl border-2 border-[#2d69df] bg-white/80 px-7 py-3 text-base font-extrabold text-[#0b2143] backdrop-blur-sm transition hover:-translate-y-0.5 hover:bg-white focus:outline-none focus-visible:ring-4 focus-visible:ring-blue-200"
						>
							<FaMagnifyingGlass aria-hidden="true" className="text-[#1759df]" />
							Explore My Options
						</Link>
					</div>

					<div className="mt-auto w-full rounded-2xl border border-white/80 bg-white/90 p-3 text-left shadow-[0_22px_70px_-28px_rgba(38,84,130,0.35)] backdrop-blur-md sm:p-5">
						<ul className="grid sm:grid-cols-2 xl:grid-cols-4">
							{homepageFeatures.map((feature, index) => {
								const Icon = feature.icon;
								const borderClass = [
									"",
									"border-t border-slate-200 sm:border-l sm:border-t-0",
									"border-t border-slate-200 xl:border-l xl:border-t-0",
									"border-t border-slate-200 sm:border-l xl:border-t-0",
								][index];
								return (
									<li key={feature.id} className={`flex gap-3 px-3 py-4 ${borderClass}`}>
										<div className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-blue-50 text-lg text-[#1759df] ring-1 ring-inset ring-blue-100">
											<Icon aria-hidden="true" />
										</div>
										<div className="min-w-0">
											<h2 className="text-sm font-extrabold text-[#0b1f3a]">{feature.title}</h2>
											<p className="mt-1 text-xs leading-5 text-slate-600">{feature.description}</p>
										</div>
									</li>
								);
							})}
						</ul>
					</div>
				</div>
			</section>
			<EdPlanSteps steps={EDPLAN_STEPS} />
			<AcademicResources resources={ACADEMIC_RESOURCES} />
		</div>
	);
};

export default HomePage;
