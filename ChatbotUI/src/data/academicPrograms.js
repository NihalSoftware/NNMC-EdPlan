export const ACADEMIC_STATS = [
	{ id: "programs", value: "66", label: "Programs" },
	{ id: "bachelors", value: "16", label: "Bachelor's" },
	{ id: "associates", value: "25", label: "Associate" },
	{ id: "certificates", value: "25", label: "Certificates" },
];

export const AREAS_OF_INTEREST = [
	{
		id: "arts-humanities",
		title: "Arts and Humanities",
		description: "Build communication, creative thinking, and cultural fluency for adaptable careers.",
		icon: "palette",
	},
	{
		id: "business-management",
		title: "Business and Management",
		description: "Develop the strategic, financial, and leadership skills organizations need.",
		icon: "briefcase",
	},
	{
		id: "computer-technology",
		title: "Computer Science and Technology",
		description: "Design, secure, and improve the digital systems that shape modern life.",
		icon: "code",
	},
	{
		id: "education",
		title: "Education",
		description: "Prepare to support learners and strengthen communities in and beyond the classroom.",
		icon: "graduation",
	},
	{
		id: "healthcare-nursing",
		title: "Healthcare and Nursing",
		description: "Turn science and compassion into meaningful work that improves patient outcomes.",
		icon: "heart",
	},
	{
		id: "public-service",
		title: "Public Service",
		description: "Study people, policy, and institutions to serve communities with confidence.",
		icon: "building",
	},
	{
		id: "science-environment",
		title: "Science and Environment",
		description: "Investigate natural systems and apply evidence to environmental challenges.",
		icon: "flask",
	},
	{
		id: "technical-trades",
		title: "Skilled and Technical Trades",
		description: "Gain practical expertise for high-demand technical and advanced manufacturing roles.",
		icon: "tools",
	},
];

const NNMC_CATALOG_PROGRAMS = [
	{ title: "Early Childhood Education, BA", category: "Bachelor of Arts", credits: 120, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=181&returnto=110" },
	{ title: "Elementary Education, BA", category: "Bachelor of Arts", credits: 120, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=182&returnto=110" },
	{ title: "Biology, BS", category: "Bachelor of Science", credits: 120, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=140&returnto=110" },
	{ title: "Environmental Science, BS", category: "Bachelor of Science", credits: 120, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=143&returnto=110" },
	{ title: "Mathematics, BS", category: "Bachelor of Science", credits: 120, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=171&returnto=110" },
	{ title: "Crime and Justice Studies, BAIS", category: "Bachelor of Arts in Integrated Studies", credits: 120, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=135&returnto=110" },
	{ title: "Humanities, BAIS", category: "Bachelor of Arts in Integrated Studies", credits: 120, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=133&returnto=110" },
	{ title: "Media & Art, BAIS", category: "Bachelor of Arts in Integrated Studies", credits: 120, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=136&returnto=110" },
	{ title: "Psychology, BAIS", category: "Bachelor of Arts in Integrated Studies", credits: 120, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=134&returnto=110" },
	{ title: "Self-Design, BAIS", category: "Bachelor of Arts in Integrated Studies", credits: 120, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=137&returnto=110" },
	{ title: "Accounting, BBA", category: "Bachelor of Business Administration", credits: 120, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=148&returnto=110" },
	{ title: "Management, BBA", category: "Bachelor of Business Administration", credits: 120, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=149&returnto=110" },
	{ title: "Project Management, BBA", category: "Bachelor of Business Administration", credits: 120, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=150&returnto=110" },
	{ title: "Electromechanical Engineering Technology, BEng", category: "Bachelor of Engineering", credits: 120, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=166&returnto=110" },
	{ title: "Information Engineering Technology, BEng", category: "Bachelor of Engineering", credits: 120, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=165&returnto=110" },
	{ title: "RN to BSN", category: "Bachelor of Science in Nursing", credits: 120, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=178&returnto=110" },
	{ title: "Business Administration, AA", category: "Associate of Arts", credits: 60, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=147&returnto=110" },
	{ title: "Criminal Justice, AA", category: "Associate of Arts", credits: 60, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=138&returnto=110" },
	{ title: "Early Childhood Education, AA", category: "Associate of Arts", credits: 60, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=179&returnto=110" },
	{ title: "Elementary Education, AA", category: "Associate of Arts", credits: 60, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=180&returnto=110" },
	{ title: "Film & Digital Media Arts (FDMA), AA", category: "Associate of Arts", credits: 60, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=132&returnto=110" },
	{ title: "General Psychology, AA", category: "Associate of Arts", credits: 60, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=139&returnto=110" },
	{ title: "Liberal Arts, AA", category: "Associate of Arts", credits: 60, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=169&returnto=110" },
	{ title: "Biology, AS", category: "Associate of Science", credits: 60, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=141&returnto=110" },
	{ title: "Chemistry, AS", category: "Associate of Science", credits: 60, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=142&returnto=110" },
	{ title: "Environmental Science, AS", category: "Associate of Science", credits: 60, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=194&returnto=110" },
	{ title: "Mathematics, AS", category: "Associate of Science", credits: 60, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=172&returnto=110" },
	{ title: "Allied Health, AAS", category: "Associate of Applied Science", credits: 60, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=174&returnto=110" },
	{ title: "Associate Degree Nursing, AAS", category: "Associate of Applied Science", credits: 68, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=176&returnto=110" },
	{ title: "Barbering, AAS", category: "Associate of Applied Science", credits: 70, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=158&returnto=110" },
	{ title: "Carpentry Technology, AAS", category: "Associate of Applied Science", credits: 60, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=261&returnto=110" },
	{ title: "Cosmetology, AAS", category: "Associate of Applied Science", credits: 85, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=160&returnto=110" },
	{ title: "Electrical Technology, AAS", category: "Associate of Applied Science", credits: 60, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=186&returnto=110" },
	{ title: "Nuclear Operations Technology, AAS", category: "Associate of Applied Science", credits: 60, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=146&returnto=110" },
	{ title: "Office Administration, AAS", category: "Associate of Applied Science", credits: 62, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=152&returnto=110" },
	{ title: "Plumbing Apprenticeship, AAS", category: "Associate of Applied Science", credits: 60, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=191&returnto=110" },
	{ title: "Plumbing Non-Apprenticeship, AAS", category: "Associate of Applied Science", credits: 60, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=188&returnto=110" },
	{ title: "Radiation Protection, AAS", category: "Associate of Applied Science", credits: 62, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=144&returnto=110" },
	{ title: "Information Engineering Technology, AEng", category: "Associate of Engineering", credits: 60, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=162&returnto=110" },
	{ title: "Pre-Engineering, AEng", category: "Associate of Engineering", credits: 60, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=163&returnto=110" },
	{ title: "Software Engineering, AEng", category: "Associate of Engineering", credits: 60, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=164&returnto=110" },
	{ title: "Administrative Assistant Certificate", category: "Certificate", credits: 32, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=153&returnto=110" },
	{ title: "Alternative Licensure Program", category: "Certificate", credits: 21, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=195&returnto=110" },
	{ title: "Barbering Certificate", category: "Certificate", credits: 54, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=159&returnto=110" },
	{ title: "Biotechnology, Certificate", category: "Certificate", credits: 21, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=258&returnto=110" },
	{ title: "Bookkeeper Certificate", category: "Certificate", credits: 22, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=154&returnto=110" },
	{ title: "Child Development Certificate (CDC)", category: "Certificate", credits: 12, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=259&returnto=110" },
	{ title: "Cosmetology Certificate", category: "Certificate", credits: 69, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=161&returnto=110" },
	{ title: "Data Science Certificate", category: "Certificate", credits: 16, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=173&returnto=110" },
	{ title: "Early Childhood Professional Certificate (ECPC)", category: "Certificate", credits: 29, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=260&returnto=110" },
	{ title: "Electrical Technology Certificate", category: "Certificate", credits: 35, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=187&returnto=110" },
	{ title: "Engineering Drawing and Computer Aided Design Certificate", category: "Certificate", credits: 18, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=167&returnto=110" },
	{ title: "Entrepreneurship Certificate", category: "Certificate", credits: 24, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=156&returnto=110" },
	{ title: "Hospitality, Tourism, and Restaurant Management Certificate", category: "Certificate", credits: 18, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=157&returnto=110" },
	{ title: "HVAC Certificate", category: "Certificate", credits: 15, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=262&returnto=110" },
	{ title: "Literary Editing And Publishing Certificate", category: "Certificate", credits: 15, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=170&returnto=110" },
	{ title: "Microsoft Office Suite Certificate", category: "Certificate", credits: 15, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=155&returnto=110" },
	{ title: "Phlebotomy Technician Certificate", category: "Certificate", credits: 17, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=175&returnto=110" },
	{ title: "Pipefitting Apprenticeship Certificate", category: "Certificate", credits: 35, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=192&returnto=110" },
	{ title: "Pipefitting Certificate", category: "Certificate", credits: 35, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=190&returnto=110" },
	{ title: "Plumbing Apprenticeship Certificate", category: "Certificate", credits: 32, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=193&returnto=110" },
	{ title: "Plumbing Certificate", category: "Certificate", credits: 35, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=189&returnto=110" },
	{ title: "Practical Nursing Certificate", category: "Certificate", credits: 52, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=177&returnto=110" },
	{ title: "Project Management Certificate", category: "Certificate", credits: 15, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=151&returnto=110" },
	{ title: "Radiation Control Technician, Certificate", category: "Certificate", credits: 32, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=145&returnto=110" },
	{ title: "Welding Certificate", category: "Certificate", credits: 24, url: "https://catalog.nnmc.edu/preview_program.php?catoid=3&poid=263&returnto=110" },
];

const AREA_DESCRIPTIONS = {
	"Arts and Humanities": "Explore Northern programs in arts, humanities, media, psychology, and liberal studies.",
	"Business and Management": "Build practical knowledge in business, accounting, management, administration, and entrepreneurship.",
	"Computer Science and Technology": "Develop technical and engineering skills for modern systems, software, and design.",
	Education: "Prepare to support learners and communities through Northern's education and licensure programs.",
	"Healthcare and Nursing": "Prepare for patient-focused work through Northern's nursing and allied health pathways.",
	"Public Service": "Study justice and public-serving disciplines that strengthen New Mexico communities.",
	"Science and Environment": "Study scientific, mathematical, environmental, nuclear, and radiation-focused fields.",
	"Skilled and Technical Trades": "Gain hands-on preparation for Northern's high-demand trade and apprenticeship pathways.",
};

const getArea = (title) => {
	const value = title.toLowerCase();
	if (/education|licensure|child development|childhood/.test(value)) return "Education";
	if (/nursing|rn to bsn|allied health|phlebotomy/.test(value)) return "Healthcare and Nursing";
	if (/criminal|crime and justice/.test(value)) return "Public Service";
	if (/humanities|media|art|psychology|liberal|literary|self-design/.test(value)) return "Arts and Humanities";
	if (/business|account|management|administration|administrative|bookkeeper|entrepreneur|hospitality|microsoft office/.test(value)) return "Business and Management";
	if (/engineering|software|data science|computer aided design/.test(value)) return "Computer Science and Technology";
	if (/biology|chemistry|environmental|mathematics|biotechnology|radiation|nuclear/.test(value)) return "Science and Environment";
	return "Skilled and Technical Trades";
};

const getDegreeType = (category) => {
	if (category.startsWith("Bachelor")) return "Bachelor's Degree";
	if (category.startsWith("Associate")) return "Associate Degree";
	return "Certificate";
};

const slugify = (value) =>
	value
		.toLowerCase()
		.replace(/&/g, " and ")
		.replace(/[^a-z0-9]+/g, "-")
		.replace(/^-|-$/g, "");

export const ACADEMIC_PROGRAMS = NNMC_CATALOG_PROGRAMS.map((program) => {
	const degreeType = getDegreeType(program.category);
	const area = getArea(program.title);
	return {
		id: slugify(program.title),
		name: program.title,
		institution: "Northern New Mexico College",
		state: "New Mexico",
		area,
		degreeType,
		duration: degreeType === "Bachelor's Degree" ? "4 years" : degreeType === "Associate Degree" ? "2 years" : "Varies",
		credits: program.credits,
		description: AREA_DESCRIPTIONS[area],
		catalogUrl: program.url,
		catalogCategory: program.category,
	};
});

export const EDPLAN_STEPS = [
	{
		id: "profile",
		title: "Create Your Profile",
		description: "Explore areas of your interest.",
	},
	{
		id: "discover",
		title: "Discover Programs",
		description: "Discover careers within that area.",
	},
	{
		id: "compare",
		title: "Review Your Options",
		description: "Discover programs within that area.",
	},
	{
		id: "plan",
		title: "Build Your Education Plan",
		description: "Build your education plan.",
	},
];

export const ACADEMIC_RESOURCES = [
	{
		id: "advising",
		title: "Academic Advising",
		description: "Bring your goals and questions to a conversation with an academic planning specialist.",
		cta: "Meet an Advisor",
		to: "/intake",
		icon: "advisor",
	},
	{
		id: "financial-aid",
		title: "Scholarships and Financial Aid",
		description: "Review the questions and resources that can make your college plan more affordable.",
		cta: "Explore Financial Aid",
		to: "/uni",
		icon: "wallet",
	},
	{
		id: "career",
		title: "Career Opportunities",
		description: "Connect program choices with practical skills, industries, and future career pathways.",
		cta: "View Career Pathways",
		to: "/career",
		icon: "compass",
	},
	{
		id: "campusbot",
		title: "Student Support through CampusBot",
		description: "See how always-available guidance can help students find the next right resource.",
		cta: "Ask CampusBot",
		to: "/NNMC",
		icon: "messages",
	},
];
