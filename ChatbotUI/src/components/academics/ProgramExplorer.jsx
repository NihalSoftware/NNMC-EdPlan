import { useMemo, useState } from "react";
import { FaFilter, FaMagnifyingGlass, FaXmark } from "react-icons/fa6";
import { AreaOfInterestGrid } from "./AcademicsSections.jsx";
import ProgramCard from "./ProgramCard.jsx";
import { uniqueSortedValues } from "../../utils/programFilters.js";

const selectClass =
	"mt-2 min-h-12 w-full border border-slate-300 bg-white px-3 py-2.5 text-sm font-bold text-slate-800 outline-none transition focus:border-[#c95f22] focus:ring-4 focus:ring-orange-100";

const ProgramExplorer = ({
	programs,
	filteredPrograms,
	areas,
	filters,
	onFilterChange,
	onClearFilters,
}) => {
	const [filtersOpen, setFiltersOpen] = useState(false);
	const degreeTypes = useMemo(() => uniqueSortedValues(programs, "degreeType"), [programs]);
	const programCounts = useMemo(
		() =>
			programs.reduce((counts, program) => {
				counts[program.area] = (counts[program.area] ?? 0) + 1;
				return counts;
			}, {}),
		[programs]
	);
	const handleAreaSelect = (area) => {
		onFilterChange("area", area);
		document.getElementById("program-results-heading")?.scrollIntoView({ block: "start" });
	};

	return (
		<section id="program-explorer" aria-labelledby="program-explorer-heading" className="scroll-mt-4 bg-[#f7f9fa] px-5 py-16 sm:px-8 sm:py-20 xl:px-12">
			<div className="mx-auto max-w-6xl">
				<AreaOfInterestGrid
					areas={areas}
					programCounts={programCounts}
					activeArea={filters.area}
					onSelectArea={handleAreaSelect}
				/>

				<div id="program-search" className="mt-20 scroll-mt-20 max-w-3xl border-t-4 border-[#c95f22] pt-8">
					<p className="text-sm font-black uppercase tracking-[0.2em] text-[#c95f22]">Program discovery</p>
					<h2 id="program-explorer-heading" className="mt-3 text-4xl font-semibold tracking-tight text-[#073b5c] sm:text-5xl">
						Find a program that fits your next step
					</h2>
					<p className="mt-4 text-lg leading-8 text-slate-600">
						Search Northern&rsquo;s catalog, then refine by area of interest or credential.
					</p>
				</div>

				<div className="mt-8 border border-slate-200 bg-white p-5 shadow-lg shadow-slate-900/5 sm:p-7">
					<div className="flex flex-col gap-4 lg:flex-row lg:items-end">
						<label className="min-w-0 flex-1 text-sm font-black text-slate-700">
							Keyword search
							<span className="relative mt-2 block">
								<FaMagnifyingGlass aria-hidden="true" className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
								<input
									type="search"
									value={filters.query}
									onChange={(event) => onFilterChange("query", event.target.value)}
									placeholder="Search by program, major, career or keyword"
									className="min-h-12 w-full border border-slate-300 py-2.5 pl-11 pr-4 text-base font-medium text-slate-900 outline-none transition placeholder:font-normal placeholder:text-slate-400 focus:border-[#c95f22] focus:ring-4 focus:ring-orange-100"
								/>
							</span>
						</label>
						<div className="flex gap-3">
							<button
								type="button"
								onClick={() => setFiltersOpen((value) => !value)}
								aria-expanded={filtersOpen}
								aria-controls="program-filter-controls"
								className="inline-flex min-h-12 flex-1 items-center justify-center gap-2 border border-slate-300 px-4 py-2.5 font-black text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-4 focus-visible:ring-orange-200 md:hidden"
							>
								<FaFilter aria-hidden="true" /> Filters
							</button>
							<button
								type="button"
								onClick={onClearFilters}
								className="inline-flex min-h-12 items-center justify-center gap-2 border border-slate-300 px-4 py-2.5 font-black text-slate-700 hover:border-orange-200 hover:bg-orange-50 hover:text-[#a94716] focus:outline-none focus-visible:ring-4 focus-visible:ring-orange-100"
							>
								<FaXmark aria-hidden="true" /> Clear filters
							</button>
						</div>
					</div>

					<div
						id="program-filter-controls"
						className={`${filtersOpen ? "grid" : "hidden"} mt-6 gap-4 border-t border-slate-100 pt-6 md:grid md:grid-cols-2`}
					>
						<label className="text-sm font-black text-slate-700">
							Area of interest
							<select value={filters.area} onChange={(event) => onFilterChange("area", event.target.value)} className={selectClass}>
								<option value="">All areas</option>
								{areas.map((area) => <option key={area.id} value={area.title}>{area.title}</option>)}
							</select>
						</label>
						<label className="text-sm font-black text-slate-700">
							Degree type
							<select value={filters.degreeType} onChange={(event) => onFilterChange("degreeType", event.target.value)} className={selectClass}>
								<option value="">All degree types</option>
								{degreeTypes.map((degreeType) => <option key={degreeType} value={degreeType}>{degreeType}</option>)}
							</select>
						</label>
					</div>

					<div className="mt-6 flex flex-col gap-2 border-t border-slate-100 pt-5 sm:flex-row sm:items-center sm:justify-between">
						<p className="font-black text-slate-900" aria-live="polite">
							{filteredPrograms.length} {filteredPrograms.length === 1 ? "program" : "programs"} found
						</p>
						<p className="text-sm font-semibold text-slate-500">Filters are saved in the page URL for easy sharing.</p>
					</div>
				</div>

				<section aria-labelledby="program-results-heading" className="mt-16 scroll-mt-6">
					<div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
						<div>
							<p className="text-sm font-black uppercase tracking-[0.2em] text-[#c95f22]">Northern&rsquo;s 2025–2026 catalog</p>
							<h2 id="program-results-heading" className="mt-2 text-4xl font-semibold tracking-tight text-[#073b5c] sm:text-5xl">
								Northern programs
							</h2>
						</div>
						<p className="max-w-md text-sm leading-6 text-slate-500">
							Program names, credential types, credits, and catalog links come from Northern New Mexico College&rsquo;s official catalog data.
						</p>
					</div>

					{filteredPrograms.length > 0 ? (
						<div className="mt-8 grid gap-6 xl:grid-cols-2">
							{filteredPrograms.map((program) => (
								<ProgramCard
									key={program.id}
									program={program}
								/>
							))}
						</div>
					) : (
						<div className="mt-8 border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
							<div className="mx-auto grid h-14 w-14 place-items-center bg-slate-100 text-xl text-slate-500">
								<FaMagnifyingGlass aria-hidden="true" />
							</div>
							<h3 className="mt-5 text-xl font-black text-slate-950">No programs found</h3>
							<p className="mx-auto mt-2 max-w-lg leading-7 text-slate-600">
								No programs match your current filters. Try removing one or more filters.
							</p>
							<button
								type="button"
								onClick={onClearFilters}
								className="mt-6 min-h-11 bg-[#c95f22] px-5 py-2.5 font-black text-white hover:bg-[#a94716] focus:outline-none focus-visible:ring-4 focus-visible:ring-orange-200"
							>
								Clear Filters
							</button>
						</div>
					)}
				</section>
			</div>
		</section>
	);
};

export default ProgramExplorer;
