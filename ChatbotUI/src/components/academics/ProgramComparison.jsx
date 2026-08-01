import { useEffect, useRef } from "react";
import { FaCodeCompare, FaXmark } from "react-icons/fa6";

export const ProgramComparisonBar = ({ programs, onRemove, onClear, onCompare }) => {
	if (programs.length < 2) return null;

	return (
		<aside
			aria-label="Program comparison selection"
			className="fixed bottom-3 left-3 right-3 z-40 rounded-2xl border border-indigo-200 bg-white/95 p-4 shadow-2xl shadow-slate-950/20 backdrop-blur sm:bottom-5 sm:left-5 sm:right-5 lg:left-[19.25rem]"
		>
			<div className="mx-auto flex max-w-7xl flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
				<div className="min-w-0">
					<p className="flex items-center gap-2 font-black text-slate-950">
						<FaCodeCompare aria-hidden="true" className="text-indigo-600" />
						{programs.length} programs selected
					</p>
					<div className="mt-2 flex max-h-20 flex-wrap gap-2 overflow-y-auto">
						{programs.map((program) => (
							<span key={program.id} className="inline-flex items-center gap-2 rounded-full bg-indigo-50 py-1 pl-3 pr-1 text-xs font-bold text-indigo-800">
								<span className="max-w-48 truncate">{program.name}</span>
								<button
									type="button"
									onClick={() => onRemove(program.id)}
									aria-label={`Remove ${program.name} from comparison`}
									className="grid h-7 w-7 place-items-center rounded-full hover:bg-indigo-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
								>
									<FaXmark aria-hidden="true" />
								</button>
							</span>
						))}
					</div>
				</div>
				<div className="flex flex-col gap-2 sm:flex-row">
					<button
						type="button"
						onClick={onClear}
						className="min-h-11 rounded-xl px-4 py-2 text-sm font-black text-slate-600 hover:bg-slate-100 focus:outline-none focus-visible:ring-4 focus-visible:ring-slate-200"
					>
						Clear all
					</button>
					<button
						type="button"
						onClick={onCompare}
						className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-2 text-sm font-black text-white hover:bg-indigo-700 focus:outline-none focus-visible:ring-4 focus-visible:ring-indigo-200"
					>
						<FaCodeCompare aria-hidden="true" />
						Compare Programs
					</button>
				</div>
			</div>
		</aside>
	);
};

export const ProgramComparisonDialog = ({ programs, open, onClose }) => {
	const closeButtonRef = useRef(null);
	const previousFocusRef = useRef(null);

	useEffect(() => {
		if (!open) return undefined;
		previousFocusRef.current = document.activeElement;
		closeButtonRef.current?.focus();

		const handleKeyDown = (event) => {
			if (event.key === "Escape") onClose();
		};
		document.addEventListener("keydown", handleKeyDown);
		return () => {
			document.removeEventListener("keydown", handleKeyDown);
			previousFocusRef.current?.focus?.();
		};
	}, [open, onClose]);

	if (!open) return null;

	return (
		<div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/70 p-4" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
			<section
				role="dialog"
				aria-modal="true"
				aria-labelledby="compare-dialog-title"
				className="max-h-[90vh] w-full max-w-6xl overflow-y-auto rounded-3xl bg-white shadow-2xl"
			>
				<header className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-200 bg-white px-5 py-5 sm:px-7">
					<div>
						<p className="text-sm font-black uppercase tracking-[0.16em] text-indigo-700">Side-by-side review</p>
						<h2 id="compare-dialog-title" className="mt-1 text-2xl font-black text-slate-950 sm:text-3xl">
							Compare programs
						</h2>
					</div>
					<button
						ref={closeButtonRef}
						type="button"
						onClick={onClose}
						aria-label="Close program comparison"
						className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-slate-100 text-slate-700 hover:bg-slate-200 focus:outline-none focus-visible:ring-4 focus-visible:ring-indigo-200"
					>
						<FaXmark aria-hidden="true" />
					</button>
				</header>
				<div className="grid gap-4 p-5 md:grid-cols-2 xl:grid-cols-3 sm:p-7">
					{programs.map((program) => (
						<article key={program.id} className="rounded-2xl border border-slate-200 p-5">
							<h3 className="text-xl font-black text-slate-950">{program.name}</h3>
							<p className="mt-1 text-sm font-bold text-indigo-700">{program.institution}</p>
							<dl className="mt-5 space-y-4 text-sm">
								{[
									["Degree type", program.degreeType],
									["Delivery", program.delivery],
									["Duration", program.duration],
									["Estimated credits", program.credits ?? "Varies"],
								].map(([label, value]) => (
									<div key={label} className="border-b border-slate-100 pb-3">
										<dt className="font-semibold text-slate-500">{label}</dt>
										<dd className="mt-1 font-black text-slate-900">{value}</dd>
									</div>
								))}
								<div>
									<dt className="font-semibold text-slate-500">Major requirements</dt>
									<dd className="mt-2">
										<ul className="list-disc space-y-1 pl-5 text-slate-700">
											{program.requirements?.map((requirement) => <li key={requirement}>{requirement}</li>)}
										</ul>
									</dd>
								</div>
								<div>
									<dt className="font-semibold text-slate-500">Career pathways</dt>
									<dd className="mt-2 text-slate-700">{program.careers?.join(", ") || "Not listed"}</dd>
								</div>
							</dl>
						</article>
					))}
				</div>
			</section>
		</div>
	);
};
