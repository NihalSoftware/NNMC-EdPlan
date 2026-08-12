import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout.jsx";
import HomePage from "./pages/HomePage.jsx";
import EducationPlanEditPage from "./pages/EducationPlanEditPage.jsx";
import ViewEducationPlanPage from "./pages/ViewEducationPlanPage.jsx";
import FindUniversityPage from "./pages/FindUniversityPage.jsx";
import CollegeDetailPage from "./pages/CollegeDetailPage.jsx";
import CareerProgramPage from "./pages/CareerProgramPage.jsx";
import ProgramExplorer from "./components/academics/ProgramExplorer.jsx";
import ScheduleGenerator from "./pages/ScheduleGenerator.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import SignupPage from "./pages/SignupPage.jsx";
import IntakeForm from "./pages/IntakeForm.jsx";

const LegacyAcademicsRedirect = () => {
	const { search } = useLocation();
	const searchParams = new URLSearchParams(search);
	const destination = ["q", "degree"].some((parameter) => searchParams.has(parameter))
		? "/programs"
		: "/career";
	return <Navigate to={`${destination}${search}`} replace />;
};

const App = () => (
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
			<Route path="/college/:unitId" element={<CollegeDetailPage />} />
		</Route>
		<Route path="/login" element={<LoginPage />} />
		<Route path="/signup" element={<SignupPage />} />
		<Route path="*" element={<Navigate to="/NNMC" replace />} />
	</Routes>
);

export default App;
