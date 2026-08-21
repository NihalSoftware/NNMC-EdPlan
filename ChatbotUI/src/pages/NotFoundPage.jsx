import { Link } from "react-router-dom";

const NotFoundPage = () => (
	<main className="grid min-h-screen place-items-center bg-slate-100 px-5 py-12 text-slate-900">
		<section
			aria-labelledby="not-found-heading"
			className="w-full max-w-2xl rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-xl sm:p-12"
		>
			<p className="text-sm font-black uppercase tracking-[0.2em] text-blue-700">
				Northern New Mexico College
			</p>
			<p className="mt-5 text-7xl font-black tracking-tight text-[#0b4770]" aria-hidden="true">
				404
			</p>
			<h1
				id="not-found-heading"
				className="mt-3 text-3xl font-black tracking-tight text-[#071a38] sm:text-4xl"
			>
				Page not found
			</h1>
			<p className="mx-auto mt-4 max-w-lg leading-7 text-slate-600">
				The page may have moved or the address may be incorrect. Return to the NNMC
				planning hub or continue exploring official programs.
			</p>
			<div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
				<Link
					to="/NNMC"
					className="inline-flex min-h-12 items-center justify-center rounded-lg bg-blue-700 px-6 py-3 font-bold text-white transition hover:bg-blue-800 focus:outline-none focus-visible:ring-4 focus-visible:ring-blue-200"
				>
					Return Home
				</Link>
				<Link
					to="/programs"
					className="inline-flex min-h-12 items-center justify-center rounded-lg border border-slate-300 bg-white px-6 py-3 font-bold text-slate-800 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-4 focus-visible:ring-blue-200"
				>
					Explore Programs
				</Link>
			</div>
		</section>
	</main>
);

export default NotFoundPage;
