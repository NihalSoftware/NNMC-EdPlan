import { lazy, Suspense, useEffect } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout.jsx";
import HomePage from "./pages/HomePage.jsx";

const CareerProgramPage = lazy(() => import("./pages/CareerProgramPage.jsx"));
const EducationPlanEditPage = lazy(() => import("./pages/EducationPlanEditPage.jsx"));
const FindUniversityPage = lazy(() => import("./pages/FindUniversityPage.jsx"));
const IntakeForm = lazy(() => import("./pages/IntakeForm.jsx"));
const LoginPage = lazy(() => import("./pages/LoginPage.jsx"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage.jsx"));
const ProgramExplorer = lazy(
	() => import("./components/academics/ProgramExplorer.jsx")
);
const ScheduleGenerator = lazy(() => import("./pages/ScheduleGenerator.jsx"));
const SignupPage = lazy(() => import("./pages/SignupPage.jsx"));
const ViewEducationPlanPage = lazy(
	() => import("./pages/ViewEducationPlanPage.jsx")
);

const LegacyAcademicsRedirect = () => {
	const { search } = useLocation();
	const searchParams = new URLSearchParams(search);
	const destination = ["q", "degree"].some((parameter) => searchParams.has(parameter))
		? "/programs"
		: "/career";
	return <Navigate to={`${destination}${search}`} replace />;
};

const ROUTE_METADATA = {
	"/NNMC": {
		title: "Northern New Mexico College Student Planning Hub",
		description:
			"Explore NNMC programs, career pathways, and semester-by-semester education plans.",
	},
	"/career": {
		title: "Career Pathways | NNMC Student Planning Hub",
		description: "Connect career pathways with Northern New Mexico College programs.",
	},
	"/programs": {
		title: "Academic Programs | NNMC Student Planning Hub",
		description: "Browse Northern New Mexico College programs and catalog requirements.",
	},
	"/uni": {
		title: "Why Northern | NNMC Student Planning Hub",
		description: "Review official Northern New Mexico College information and resources.",
	},
	"/intake": {
		title: "Academic History | NNMC Student Planning Hub",
		description: "Record academic history for a personalized Northern education plan.",
	},
	"/educationplan": {
		title: "Create Education Plan | NNMC Student Planning Hub",
		description: "Build a semester-by-semester Northern New Mexico College education plan.",
	},
	"/schedule-generator": {
		title: "Schedule Generator | NNMC Student Planning Hub",
		description: "Review possible course schedules for an NNMC education plan.",
	},
	"/view": {
		title: "Saved Education Plans | NNMC Student Planning Hub",
		description: "Review saved Northern New Mexico College education plans.",
	},
	"/login": {
		title: "Log In | NNMC Student Planning Hub",
		description: "Log in to the Northern New Mexico College student planning hub.",
	},
	"/signup": {
		title: "Create Account | NNMC Student Planning Hub",
		description: "Create an NNMC student planning hub account.",
	},
};

const PRIVATE_ROUTES = new Set([
	"/educationplan",
	"/intake",
	"/login",
	"/schedule-generator",
	"/signup",
	"/view",
]);

const RouteMetadata = () => {
	const { pathname } = useLocation();

	useEffect(() => {
		const metadata = ROUTE_METADATA[pathname];
		document.title = metadata?.title || "Page Not Found | NNMC Student Planning Hub";

		const description = document.querySelector('meta[name="description"]');
		if (description && metadata?.description) {
			description.setAttribute("content", metadata.description);
		}

		let robots = document.querySelector('meta[name="robots"]');
		if (!robots) {
			robots = document.createElement("meta");
			robots.setAttribute("name", "robots");
			document.head.appendChild(robots);
		}
		robots.setAttribute(
			"content",
			metadata && !PRIVATE_ROUTES.has(pathname) ? "index, follow" : "noindex, nofollow"
		);

		let canonical = document.querySelector('link[rel="canonical"]');
		if (!canonical) {
			canonical = document.createElement("link");
			canonical.setAttribute("rel", "canonical");
			document.head.appendChild(canonical);
		}
		canonical.setAttribute("href", new URL(pathname, window.location.origin).href);
	}, [pathname]);

	return null;
};

const App = () => (
	<Suspense
		fallback={
			<div className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-700">
				<p role="status" aria-live="polite">
					Loading page…
				</p>
			</div>
		}
	>
		<RouteMetadata />
		<Routes>
			<Route element={<AppLayout />}>
				<Route path="/" element={<Navigate to="/NNMC" replace />} />
				<Route path="/NNMC" element={<HomePage />} />
				<Route path="/intake" element={<IntakeForm />} />
				<Route path="/educationplan" element={<EducationPlanEditPage />} />
				<Route path="/career" element={<CareerProgramPage />} />
				<Route path="/academics" element={<LegacyAcademicsRedirect />} />
				<Route path="/programs" element={<ProgramExplorer />} />
				<Route path="/schedule-generator" element={<ScheduleGenerator />} />
				<Route path="/view" element={<ViewEducationPlanPage />} />
				<Route path="/uni" element={<FindUniversityPage />} />
				<Route path="/compare" element={<Navigate to="/uni" replace />} />
				<Route
					path="/college/:unitId"
					element={<Navigate to="/uni#nnmc-college-details" replace />}
				/>
			</Route>
			<Route path="/login" element={<LoginPage />} />
			<Route path="/signup" element={<SignupPage />} />
			<Route path="*" element={<NotFoundPage />} />
		</Routes>
	</Suspense>
);

export default App;
