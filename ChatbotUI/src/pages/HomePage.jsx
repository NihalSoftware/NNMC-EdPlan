import { Link } from "react-router-dom";
import {
	FaArrowRight,
	FaBookOpen,
	FaComments,
	FaCompass,
	FaUserGroup,
	FaWallet,
} from "react-icons/fa6";
import { load } from "../utils/storage.js";
import { INSTITUTION } from "../config/institution.js";
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
		<section className="w-full min-h-screen flex flex-col items-center justify-center py-12 px-6 bg-gradient-to-br from-sky-50 via-white to-amber-50">
			<div className="container mx-auto px-4 sm:px-6 lg:px-8">
				<div className="max-w-4xl mx-auto text-center space-y-8">
					<img
						src={INSTITUTION.logoUrl}
						alt="Northern New Mexico College"
						className="h-24 w-auto object-contain mx-auto"
					/>
					<h1 className="font-heading text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight text-foreground">
						Find Your Future <span className="text-[#0069e0]">@Northern</span>
					</h1>

					<h2 className="text-4xl font-bold text-slate-900">
						Small community. Great opportunity.
					</h2>

					<p className="text-lg text-slate-600">
						Explore Northern New Mexico College programs, connect them to career
						goals, and build a personalized path toward graduation.
					</p>
				</div>
			</div>

			<div className="max-w-3xl text-center space-y-6">
				<div className="flex flex-wrap items-center justify-center gap-4 mt-5">
					{firstName ? (
						<div className="px-6 py-3 rounded-lg border border-slate-300 text-slate-700 font-semibold">
							Hi {firstName}
						</div>
					) : (
						<Link
							to="/login"
							className="px-6 py-3 rounded-lg border border-slate-300 text-slate-700 font-semibold hover:border-slate-500"
						>
							Login
						</Link>
					)}
					<Link
						to="/career"
						className="px-6 py-3 rounded-lg bg-[#0069e0] hover:bg-[#1977e3] text-white font-semibold shadow"
					>
						Explore NNMC Programs
					</Link>
				</div>

				<div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-slate-600">
					<div className="bg-white rounded-lg shadow p-4">
						Build an NNMC degree plan tailored to your goals.
					</div>
					<div className="bg-white rounded-lg shadow p-4">
						Review official NNMC cost and financial-aid information.
					</div>
					<div className="bg-white rounded-lg shadow p-4">
						Connect programs with career paths and practical next steps.
					</div>
				</div>
			</div>
		</section>
		<EdPlanSteps steps={EDPLAN_STEPS} />
		<AcademicResources resources={ACADEMIC_RESOURCES} />
		</div>
	);
};

export default HomePage;
