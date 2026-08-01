import { Outlet } from "react-router-dom";
import { useState } from "react";
import Navigation from "./Navigation.jsx";

const AppLayout = () => {
	const [open, setOpen] = useState(false);

	return (
		<div className="min-h-screen flex flex-col lg:flex-row bg-slate-100 text-slate-900">
			{/* Mobile header with hamburger - inside layout flow so it won't cover page content */}
			<header className="w-full lg:hidden bg-white border-b">
				<div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
					<button
						type="button"
						aria-label={open ? "Close menu" : "Open menu"}
						onClick={() => setOpen((s) => !s)}
						className="p-2 rounded-md bg-white shadow"
					>
						{open ? (
							<span className="text-2xl text-slate-800">&times;</span>
						) : (
							<span className="flex flex-col gap-1">
								<span className="block w-6 h-0.5 bg-slate-800" />
								<span className="block w-6 h-0.5 bg-slate-800" />
								<span className="block w-6 h-0.5 bg-slate-800" />
							</span>
						)}
					</button>
					<p className="text-xl font-bold text-slate-900">NNMC Student Hub</p>
					<div style={{ width: 40 }} />
				</div>
			</header>

			<Navigation open={open} setOpen={setOpen} />

			{/* Backdrop for mobile when menu is open */}
			{open && <div className="fixed inset-0 bg-black/30 z-40 lg:hidden" onClick={() => setOpen(false)} />}

			<main className="flex-1 w-full min-h-screen overflow-y-auto lg:ml-72">
				<Outlet />
			</main>
		</div>
	);
};

export default AppLayout;
