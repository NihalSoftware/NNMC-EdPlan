import { useCallback, useEffect, useMemo } from "react";
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
} from "../components/academics/AcademicsSections.jsx";
import ProgramExplorer from "../components/academics/ProgramExplorer.jsx";
import { filterPrograms } from "../utils/programFilters.js";

const META_DESCRIPTION =
	"Discover Northern New Mexico College academic programs and build a personalized semester-by-semester education plan with EdPlan AI.";

const metadata = [
	["name", "description", META_DESCRIPTION],
	["property", "og:title", "Academics | Northern New Mexico College"],
	["property", "og:description", META_DESCRIPTION],
	["name", "twitter:title", "Academics | Northern New Mexico College"],
	["name", "twitter:description", META_DESCRIPTION],
];

const AcademicsPage = () => {
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

	const handleFilterChange = useCallback(
		(key, value) => {
			const parameterByFilter = {
				query: "q",
				area: "area",
				degreeType: "degree",
			};
			const parameter = parameterByFilter[key];
			const next = new URLSearchParams(searchParams);
			if (value) next.set(parameter, value);
			else next.delete(parameter);
			setSearchParams(next, { replace: true });
		},
		[searchParams, setSearchParams]
	);

	return (
		<div className="min-h-screen overflow-x-clip bg-white">
			<AcademicsHero />
			<AcademicStats stats={ACADEMIC_STATS} />
			<ProgramExplorer
				programs={ACADEMIC_PROGRAMS}
				filteredPrograms={filteredPrograms}
				areas={AREAS_OF_INTEREST}
				filters={filters}
				onFilterChange={handleFilterChange}
				onClearFilters={() => setSearchParams({}, { replace: true })}
			/>
			<EdPlanSteps steps={EDPLAN_STEPS} />
			<AcademicResources resources={ACADEMIC_RESOURCES} />
		</div>
	);
};

export default AcademicsPage;
