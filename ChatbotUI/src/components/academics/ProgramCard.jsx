import { Link } from "react-router-dom";
import {
	FaArrowRight,
	FaCheck,
	FaClock,
	FaCodeCompare,
	FaGraduationCap,
	FaLaptop,
	FaLocationDot,
	FaPlus,
} from "react-icons/fa6";

const formatBadgeClass = {
	Online: "bg-sky-50 text-sky-700 ring-sky-200",
	Hybrid: "bg-violet-50 text-violet-700 ring-violet-200",
	"On Campus": "bg-emerald-50 text-emerald-700 ring-emerald-200",
};

const ProgramCard = ({
	program,
	isCompared,
	isComparisonDisabled,
	onToggleCompare,
	isAdded,
	onToggleAdded,
}) => (
	<article className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition duration-200 hover:-translate-y-1 hover:shadow-lg">
		<div className="flex flex-wrap items-start justify-between gap-3">
			<span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-black uppercase tracking-wide text-slate-600">
				{program.degreeType}
			</span>
			<span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-black ring-1 ${formatBadgeClass[program.delivery]}`}>
				<FaLaptop aria-hidden="true" />
				{program.delivery}
			</span>
		</div>

		<h3 className="mt-5 text-2xl font-black leading-tight text-slate-950">{program.name}</h3>
		<p className="mt-2 flex items-center gap-2 text-sm font-bold text-slate-500">
			<FaLocationDot aria-hidden="true" className="text-indigo-600" />
			{program.institution} · {program.state}
		</p>
		<p className="mt-4 leading-7 text-slate-600">{program.description}</p>

		<dl className="mt-6 grid grid-cols-2 gap-3 border-y border-slate-100 py-5 text-sm">
			<div>
				<dt className="flex items-center gap-2 font-semibold text-slate-500">
					<FaClock aria-hidden="true" /> Duration
				</dt>
				<dd className="mt-1 font-black text-slate-900">{program.duration}</dd>
			</div>
			<div>
				<dt className="flex items-center gap-2 font-semibold text-slate-500">
					<FaGraduationCap aria-hidden="true" /> Est. credits
				</dt>
				<dd className="mt-1 font-black text-slate-900">{program.credits ?? "Varies"}</dd>
			</div>
		</dl>

		{program.careers?.length > 0 && (
			<div className="mt-5">
				<p className="text-xs font-black uppercase tracking-wider text-slate-500">Career pathways</p>
				<ul className="mt-2 flex flex-wrap gap-2" aria-label={`Career pathways for ${program.name}`}>
					{program.careers.slice(0, 3).map((career) => (
						<li key={career} className="rounded-lg bg-indigo-50 px-2.5 py-1 text-xs font-bold text-indigo-700">
							{career}
						</li>
					))}
				</ul>
			</div>
		)}

		<div className="mt-auto grid gap-3 pt-7 sm:grid-cols-2">
			<Link
				to={`/career?program=${encodeURIComponent(program.name)}`}
				className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-black text-slate-700 transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 focus:outline-none focus-visible:ring-4 focus-visible:ring-indigo-200"
			>
				View Program
				<FaArrowRight aria-hidden="true" />
			</Link>
			<button
				type="button"
				onClick={() => onToggleCompare(program.id)}
				aria-pressed={isCompared}
				disabled={isComparisonDisabled}
				title={isComparisonDisabled ? "Remove a program before selecting another" : undefined}
				className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-black transition focus:outline-none focus-visible:ring-4 focus-visible:ring-indigo-200 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400 ${
					isCompared
						? "border-indigo-600 bg-indigo-600 text-white hover:bg-indigo-700"
						: "border-slate-300 text-slate-700 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700"
				}`}
			>
				{isCompared ? <FaCheck aria-hidden="true" /> : <FaCodeCompare aria-hidden="true" />}
				{isCompared ? "Selected" : "Compare"}
			</button>
			<button
				type="button"
				onClick={() => onToggleAdded(program.id)}
				aria-pressed={isAdded}
				className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-black transition focus:outline-none focus-visible:ring-4 focus-visible:ring-indigo-200 sm:col-span-2 ${
					isAdded
						? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200"
						: "bg-slate-950 text-white hover:bg-indigo-700"
				}`}
			>
				{isAdded ? <FaCheck aria-hidden="true" /> : <FaPlus aria-hidden="true" />}
				{isAdded ? "Added to Education Plan" : "Add to Education Plan"}
			</button>
		</div>
	</article>
);

export default ProgramCard;
