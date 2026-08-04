import { Link } from "react-router-dom";
import {
	FaArrowRight,
	FaClock,
	FaGraduationCap,
	FaPlus,
} from "react-icons/fa6";
import { getEducationPlanUrl } from "../../utils/catalogProgramSelection.js";

const ProgramCard = ({ program }) => (
	<article className="flex h-full flex-col border border-slate-200 border-t-4 border-t-[#073b5c] bg-white p-6 shadow-sm transition duration-200 hover:-translate-y-1 hover:border-t-[#c95f22] hover:shadow-lg">
		<div className="flex flex-wrap items-start gap-3">
			<span className="bg-slate-100 px-3 py-1 text-xs font-black uppercase tracking-wide text-slate-600">
				{program.degreeType}
			</span>
		</div>

		<h3 className="mt-5 text-2xl font-semibold leading-tight text-[#073b5c]">{program.name}</h3>

		<dl className="mt-6 grid grid-cols-2 gap-3 border-y border-slate-100 py-5 text-sm">
			<div>
				<dt className="flex items-center gap-2 font-semibold text-slate-500">
					<FaClock aria-hidden="true" /> Typical duration
				</dt>
				<dd className="mt-1 font-black text-slate-900">{program.duration}</dd>
			</div>
			<div>
				<dt className="flex items-center gap-2 font-semibold text-slate-500">
					<FaGraduationCap aria-hidden="true" /> Total Credits
				</dt>
				<dd className="mt-1 font-black text-slate-900">{program.credits ?? "Varies"}</dd>
			</div>
		</dl>

		<div className="mt-auto grid gap-3 pt-7 sm:grid-cols-2">
			<a
				href={program.catalogUrl}
				target="_blank"
				rel="noreferrer"
				className="inline-flex min-h-11 items-center justify-center gap-2 border border-slate-300 px-4 py-2.5 text-sm font-black text-slate-700 transition hover:border-[#073b5c] hover:bg-[#e7f0f5] hover:text-[#073b5c] focus:outline-none focus-visible:ring-4 focus-visible:ring-sky-200"
			>
				View Official Catalog
				<FaArrowRight aria-hidden="true" />
			</a>
			<Link
				to={getEducationPlanUrl(program)}
				className="inline-flex min-h-11 items-center justify-center gap-2 bg-[#c95f22] px-4 py-2.5 text-sm font-black text-white transition hover:bg-[#a94716] focus:outline-none focus-visible:ring-4 focus-visible:ring-orange-200"
			>
				<FaPlus aria-hidden="true" />
				Add to Education Plan
			</Link>
		</div>
	</article>
);

export default ProgramCard;
