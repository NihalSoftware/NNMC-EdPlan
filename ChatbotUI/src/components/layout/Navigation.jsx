import { NavLink, useLocation, useNavigate } from "react-router-dom";
import clsx from "clsx";
import { load, remove } from "../../utils/storage.js";
import {
	FaBookOpen,
	FaBuildingColumns,
	FaClipboardList,
	FaGraduationCap,
	FaHouse,
	FaRegBookmark,
	FaRegCompass,
	FaRightFromBracket,
} from "react-icons/fa6";
import { INSTITUTION } from "../../config/institution.js";

const NavItem = ({ to, label, icon: Icon, badge, onClick }) => (
	<NavLink
		to={to}
		onClick={onClick}
		className={({ isActive }) =>
			clsx(
				"group flex w-full items-center gap-4 rounded-xl px-4 py-3 text-left font-semibold transition",
				isActive
					? "bg-indigo-50 text-indigo-600 shadow-sm ring-1 ring-indigo-100"
					: "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
			)
		}
	>
		{Icon && <Icon className="h-5 w-5 shrink-0" />}
		<span className="min-w-0 flex-1 truncate">{label}</span>
		{badge && (
			<span className="rounded-md bg-gradient-to-r from-indigo-500 to-violet-600 px-2 py-0.5 text-[10px] font-black uppercase tracking-wide text-white shadow-sm">
				{badge}
			</span>
		)}
	</NavLink>
);

const Navigation = ({ open, setOpen }) => {
	const location = useLocation();
	const navigate = useNavigate();
	const isAuthenticated = Boolean(load("AuthToken"));
	const profile = load("UserProfile");
	const firstName =
		typeof profile?.first_name === "string"
			? profile.first_name
			: typeof profile?.firstName === "string"
			? profile.firstName
			: "";

	const buttonLabel = isAuthenticated
		? "Logout"
		: location.pathname === "/login"
		? "Sign up"
		: "Login";

	const closeMenu = () => setOpen && setOpen(false);

	const handleAuthClick = () => {
		if (isAuthenticated) {
			remove("AuthToken");
			remove("UserEmail");
			remove("UserProfile");
			navigate("/login");
			return;
		}
		navigate(location.pathname === "/login" ? "/signup" : "/login");
	};

	return (
		<aside
			className={clsx(
				"flex flex-col border-r border-slate-200 bg-white shadow-sm",
				open ? "fixed inset-y-0 left-0 z-50 h-full w-72 overflow-y-auto" : "hidden",
				"lg:fixed lg:left-0 lg:top-0 lg:block lg:h-screen lg:w-72 lg:overflow-y-auto"
			)}
		>
			<header className="flex items-center justify-between gap-4 border-b border-slate-100 p-6">
				<div className="flex items-center gap-3">
					<button
						type="button"
						onClick={closeMenu}
						className="rounded-md p-2 hover:bg-slate-100 lg:hidden"
						aria-label="Close menu"
					>
						<span className="text-xl text-slate-700">x</span>
					</button>

					<img
						src={INSTITUTION.logoUrl}
						alt="Northern New Mexico College"
						className="h-10 w-10 rounded-lg bg-white object-contain p-1"
					/>
					<div>
						<p className="text-2xl font-black text-slate-950">NNMC</p>
						<p className="text-xs font-semibold text-slate-500">
							Northern New Mexico College
						</p>
					</div>
				</div>
			</header>

			<nav className="flex flex-col gap-2 px-5 py-7">
				<NavItem to="/home" label="Home" icon={FaHouse} onClick={closeMenu} />
				<NavItem to="/career" label="Career and Program" icon={FaRegCompass} onClick={closeMenu} />
				<NavItem to="/academics" label="Explore Programs" icon={FaGraduationCap} onClick={closeMenu} />
				<NavItem to="/intake" label="Onboarding Form" icon={FaClipboardList} onClick={closeMenu} />
				<NavItem to="/uni" label="NNMC Overview" icon={FaBuildingColumns} onClick={closeMenu} />
				<NavItem to="/educationplan" label="Create Education Plan" icon={FaBookOpen} onClick={closeMenu} />
				{/*<NavItem to="/schedule-generator" label="Schedule Generator" icon={FaCalendarAlt} onClick={closeMenu} />*/}
				<NavItem to="/view" label="Saved Plans" icon={FaRegBookmark} onClick={closeMenu} />
			</nav>
			<footer className="border-t border-slate-50 p-6">
				<div className="flex items-center justify-between gap-3">
					{isAuthenticated && firstName && (
						<span className="text-md font-medium text-slate-600">{firstName}</span>
					)}
					<button
						type="button"
						onClick={handleAuthClick}
						className="inline-flex items-center gap-3 text-lg font-medium text-slate-600 hover:text-indigo-600"
					>
						<FaRightFromBracket />
						{buttonLabel}
					</button>
				</div>
			</footer>
		</aside>
	);
};

export default Navigation;
