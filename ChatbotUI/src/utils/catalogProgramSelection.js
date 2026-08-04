const getProgramMetadata = (program = {}) => program.metadata_json || {};

export const getCatalogProgramId = (program = {}) => {
	const metadata = getProgramMetadata(program);
	const directId = program.catalog_program_id || metadata.catalog_program_id;
	if (directId) return String(directId);

	const catalogUrl = program.catalogUrl || program.catalog_url || metadata.catalog_url;
	if (!catalogUrl) return "";

	try {
		return new URL(catalogUrl).searchParams.get("poid") || "";
	} catch {
		return "";
	}
};

export const getEducationPlanUrl = (program) => {
	const catalogProgramId = getCatalogProgramId(program);
	return catalogProgramId
		? `/educationplan?catalogProgram=${encodeURIComponent(catalogProgramId)}`
		: "/educationplan";
};

export const findProgramByCatalogId = (programs = [], catalogProgramId = "") => {
	const requestedId = String(catalogProgramId || "").trim();
	if (!requestedId) return null;
	return (
		programs.find((program) => getCatalogProgramId(program) === requestedId) ||
		null
	);
};
