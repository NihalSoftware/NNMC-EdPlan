import { useCallback, useEffect, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { FaMagnifyingGlass, FaXmark } from "react-icons/fa6";
import ProgramCard from "./ProgramCard.jsx";
import {
	ACADEMIC_PROGRAMS,
	AREAS_OF_INTEREST,
} from "../../data/academicPrograms.js";
import {
	filterPrograms,
	uniqueSortedValues,
} from "../../utils/programFilters.js";

const META_DESCRIPTION =
	"Explore Northern New Mexico College programs by area of interest and credential, then add a selected program to your education plan.";

const metadata = [
	["name", "description", META_DESCRIPTION],
	["property", "og:title", "Explore Programs | Northern New Mexico College"],
	["property", "og:description", META_DESCRIPTION],
	["name", "twitter:title", "Explore Programs | Northern New Mexico College"],
	["name", "twitter:description", META_DESCRIPTION],
];

const selectClass =
	"mt-1.5 h-11 w-full border border-slate-300 bg-white px-3 text-sm font-bold normal-case tracking-normal text-slate-800 outline-none transition focus:border-[#c95f22] focus:ring-4 focus:ring-orange-100";

const ProgramExplorer = () => {
	const [searchParams, setSearchParams] = useSearchParams();
	const filters = useMemo(
		() => ({
			query: searchParams.get("q") ?? "",
			area: searchParams.get("area") ?? "",
			degreeType: searchParams.get("degree") ?? "",
		}),
		[searchParams]
	);
	const filteredPrograms = useMemo(
		() => filterPrograms(ACADEMIC_PROGRAMS, filters),
		[filters]
	);
	const targetedProgramId = searchParams.get("program") ?? "";
	const degreeTypes = useMemo(
		() => uniqueSortedValues(ACADEMIC_PROGRAMS, "degreeType"),
		[]
	);

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

		document.title = "Explore Programs | Northern New Mexico College";
		return () => {
			document.title = previousTitle;
			previousMetadata.forEach(({ element, created, previousContent }) => {
				if (created) element.remove();
				else if (previousContent === null) element.removeAttribute("content");
				else element.setAttribute("content", previousContent);
			});
		};
	}, []);

	useEffect(() => {
		if (!targetedProgramId || !filteredPrograms.some((program) => program.id === targetedProgramId)) return;

		const animationFrame = window.requestAnimationFrame(() => {
			const programCard = document.getElementById(`program-${targetedProgramId}`);
			programCard?.scrollIntoView({ behavior: "smooth", block: "center" });
			programCard?.focus({ preventScroll: true });
		});

		return () => window.cancelAnimationFrame(animationFrame);
	}, [filteredPrograms, targetedProgramId]);

	const handleFilterChange = useCallback(
		(key, value) => {
			const parameterByFilter = {
				query: "q",
				area: "area",
				degreeType: "degree",
			};
			const parameter = parameterByFilter[key];
			const next = new URLSearchParams(searchParams);
			next.delete("program");
			if (value) next.set(parameter, value);
			else next.delete(parameter);
			setSearchParams(next, { replace: true });
		},
		[searchParams, setSearchParams]
	);

	const handleClearFilters = useCallback(
		() => setSearchParams({}, { replace: true }),
		[setSearchParams]
	);

	return (
		<div className="min-h-screen overflow-x-clip bg-[#f7f9fa]">
			<h1 className="sr-only">Explore Programs</h1>
			<section id="program-explorer" aria-labelledby="program-explorer-heading" className="scroll-mt-4 bg-[#f7f9fa] px-5 py-16 sm:px-8 sm:py-20 xl:px-12">
			<div className="mx-auto max-w-6xl">
				<div id="program-search" className="scroll-mt-20 max-w-5xl border-t-4 border-[#c95f22] pt-8">
					<p className="text-sm font-black uppercase tracking-[0.2em] text-[#c95f22]">Program discovery</p>
					<h2 id="program-explorer-heading" className="mt-3 text-4xl font-semibold tracking-tight text-[#073b5c] sm:text-5xl">
						Find Your Best-Fit Program
					</h2>
					<p className="mt-4 text-xl  text-[#073b5c]">
						Explore Northern’s programs by area of interest or degrees awarded and find the right fit for your goals.

					</p>
				</div>

				<div
					role="search"
					aria-label="Program filters"
					className="mt-6 border border-slate-200 bg-white p-4 shadow-sm"
				>
					<div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)_minmax(0,1fr)_auto] lg:items-end">
						<label className="min-w-0 text-xs font-black uppercase tracking-wide text-slate-600">
							Program search
							<span className="relative mt-1.5 block">
								<FaMagnifyingGlass aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
								<input
									type="search"
									value={filters.query}
									onChange={(event) => handleFilterChange("query", event.target.value)}
									placeholder="Search programs"
									className="h-11 w-full border border-slate-300 py-2 pl-9 pr-3 text-sm font-semibold normal-case tracking-normal text-slate-900 outline-none transition placeholder:font-normal placeholder:text-slate-400 focus:border-[#c95f22] focus:ring-4 focus:ring-orange-100"
								/>
							</span>
						</label>
						<label className="min-w-0 text-xs font-black uppercase tracking-wide text-slate-600">
							Area of interest
							<select value={filters.area} onChange={(event) => handleFilterChange("area", event.target.value)} className={selectClass}>
								<option value="">All areas</option>
								{AREAS_OF_INTEREST.map((area) => <option key={area.id} value={area.title}>{area.title}</option>)}
							</select>
						</label>
						<label className="min-w-0 text-xs font-black uppercase tracking-wide text-slate-600">
							Degree type
							<select value={filters.degreeType} onChange={(event) => handleFilterChange("degreeType", event.target.value)} className={selectClass}>
								<option value="">All degree types</option>
								{degreeTypes.map((degreeType) => <option key={degreeType} value={degreeType}>{degreeType}</option>)}
							</select>
						</label>
						<button
							type="button"
							onClick={handleClearFilters}
							aria-label="Clear filters"
							className="inline-flex h-11 items-center justify-center gap-2 border border-slate-300 px-3 text-sm font-black text-slate-700 transition hover:border-orange-200 hover:bg-orange-50 hover:text-[#a94716] focus:outline-none focus-visible:ring-4 focus-visible:ring-orange-100 sm:col-span-2 lg:col-span-1"
						>
							<FaXmark aria-hidden="true" /> Clear
						</button>
					</div>

					<div className="mt-3 border-t border-slate-100 pt-3">
						<p className="text-sm font-black text-slate-900" aria-live="polite">
							{filteredPrograms.length} {filteredPrograms.length === 1 ? "program" : "programs"} found
						</p>
					</div>
				</div>

				<section aria-labelledby="program-results-heading" className="mt-16 scroll-mt-6">
					<div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
						<div>
							<p className="text-sm font-black uppercase tracking-[0.2em] text-[#c95f22]">Northern&rsquo;s 2025–2026 catalog</p>
							<h2 id="program-results-heading" className="mt-2 text-4xl font-semibold tracking-tight text-[#073b5c] sm:text-5xl">
								Northern Programs
							</h2>
						</div>
						<p className="max-w-md text-sm leading-6 text-slate-500">
							Program names, degree, credits, and catalog links data come from Northern New Mexico College&rsquo;s official catalog.
						</p>
					</div>

					{filteredPrograms.length > 0 ? (
						<div className="mt-8 grid gap-6 xl:grid-cols-2">
							{filteredPrograms.map((program) => (
								<ProgramCard
									key={program.id}
									program={program}
									isTargeted={program.id === targetedProgramId}
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
								onClick={handleClearFilters}
								className="mt-6 min-h-11 bg-[#c95f22] px-5 py-2.5 font-black text-white hover:bg-[#a94716] focus:outline-none focus-visible:ring-4 focus-visible:ring-orange-200"
							>
								Clear Filters
							</button>
						</div>
					)}
				</section>
			</div>
			</section>
		</div>
	);
};

export default ProgramExplorer;
