import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
	ACADEMIC_PROGRAMS,
	ACADEMIC_RESOURCES,
	ACADEMIC_STATS,
	AREAS_OF_INTEREST,
	EDPLAN_STEPS,
} from "../data/academicPrograms.js";
import {
	AcademicResources,
	AcademicStats,
	AcademicsHero,
	EdPlanSteps,
	InstitutionalCTA,
} from "../components/academics/AcademicsSections.jsx";
import ProgramExplorer from "../components/academics/ProgramExplorer.jsx";
import {
	ProgramComparisonBar,
	ProgramComparisonDialog,
} from "../components/academics/ProgramComparison.jsx";
import { filterPrograms, toggleComparedProgram } from "../utils/programFilters.js";

const META_DESCRIPTION =
	"Discover academic programs, compare degree options and build a personalized semester-by-semester education plan with StudentSpace.ai and EdPlan AI.";

const metadata = [
	["name", "description", META_DESCRIPTION],
	["property", "og:title", "Explore Academic Programs and Education Plans | StudentSpace.ai"],
	["property", "og:description", META_DESCRIPTION],
	["name", "twitter:title", "Explore Academic Programs and Education Plans | StudentSpace.ai"],
	["name", "twitter:description", META_DESCRIPTION],
];

const AcademicsPage = () => {
	const [searchParams, setSearchParams] = useSearchParams();
	const [comparedIds, setComparedIds] = useState([]);
	const [addedIds, setAddedIds] = useState([]);
	const [comparisonOpen, setComparisonOpen] = useState(false);
	const filters = useMemo(
		() => ({
			query: searchParams.get("q") ?? "",
			area: searchParams.get("area") ?? "",
			degreeType: searchParams.get("degree") ?? "",
			delivery: searchParams.get("format") ?? "",
			location: searchParams.get("location") ?? "",
		}),
		[searchParams]
	);
	const filteredPrograms = useMemo(
		() => filterPrograms(ACADEMIC_PROGRAMS, filters),
		[filters]
	);
	const comparedPrograms = useMemo(
		() => comparedIds.map((id) => ACADEMIC_PROGRAMS.find((program) => program.id === id)).filter(Boolean),
		[comparedIds]
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

		document.title = "Explore Academic Programs and Education Plans | StudentSpace.ai";
		return () => {
			document.title = previousTitle;
			previousMetadata.forEach(({ element, created, previousContent }) => {
				if (created) element.remove();
				else if (previousContent === null) element.removeAttribute("content");
				else element.setAttribute("content", previousContent);
			});
		};
	}, []);

	const handleFilterChange = useCallback(
		(key, value) => {
			const parameterByFilter = {
				query: "q",
				area: "area",
				degreeType: "degree",
				delivery: "format",
				location: "location",
			};
			const parameter = parameterByFilter[key];
			const next = new URLSearchParams(searchParams);
			if (value) next.set(parameter, value);
			else next.delete(parameter);
			setSearchParams(next, { replace: true });
		},
		[searchParams, setSearchParams]
	);

	const handleToggleCompare = useCallback((programId) => {
		setComparedIds((selectedIds) => toggleComparedProgram(selectedIds, programId));
	}, []);

	const handleToggleAdded = useCallback((programId) => {
		setAddedIds((selectedIds) =>
			selectedIds.includes(programId)
				? selectedIds.filter((id) => id !== programId)
				: [...selectedIds, programId]
		);
	}, []);

	const closeComparison = useCallback(() => setComparisonOpen(false), []);

	return (
		<div className={`min-h-screen overflow-x-hidden bg-slate-50 ${comparedPrograms.length >= 2 ? "pb-80 sm:pb-40" : ""}`}>
			<AcademicsHero />
			<AcademicStats stats={ACADEMIC_STATS} />
			<ProgramExplorer
				programs={ACADEMIC_PROGRAMS}
				filteredPrograms={filteredPrograms}
				areas={AREAS_OF_INTEREST}
				filters={filters}
				onFilterChange={handleFilterChange}
				onClearFilters={() => setSearchParams({}, { replace: true })}
				comparedIds={comparedIds}
				onToggleCompare={handleToggleCompare}
				addedIds={addedIds}
				onToggleAdded={handleToggleAdded}
			/>
			<EdPlanSteps steps={EDPLAN_STEPS} />
			<AcademicResources resources={ACADEMIC_RESOURCES} />
			<InstitutionalCTA />
			<ProgramComparisonBar
				programs={comparedPrograms}
				onRemove={handleToggleCompare}
				onClear={() => setComparedIds([])}
				onCompare={() => setComparisonOpen(true)}
			/>
			<ProgramComparisonDialog
				programs={comparedPrograms}
				open={comparisonOpen}
				onClose={closeComparison}
			/>
		</div>
	);
};

export default AcademicsPage;
