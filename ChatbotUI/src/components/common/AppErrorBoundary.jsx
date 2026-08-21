import { Component } from "react";

class AppErrorBoundary extends Component {
	constructor(props) {
		super(props);
		this.state = { hasError: false };
	}

	static getDerivedStateFromError() {
		return { hasError: true };
	}

	componentDidCatch(error, errorInfo) {
		console.error("[AppErrorBoundary] Unhandled application error", {
			error,
			errorInfo,
		});
	}

	handleRetry = () => {
		window.location.reload();
	};

	render() {
		if (!this.state.hasError) {
			return this.props.children;
		}

		return (
			<main className="grid min-h-screen place-items-center bg-slate-100 px-5 py-12 text-slate-900">
				<section
					aria-labelledby="application-error-heading"
					className="w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-xl sm:p-10"
				>
					<p className="text-sm font-black uppercase tracking-[0.18em] text-blue-700">
						NNMC Student Planning Hub
					</p>
					<h1
						id="application-error-heading"
						className="mt-3 text-3xl font-black tracking-tight text-[#071a38]"
					>
						We could not load this page
					</h1>
					<p className="mt-4 leading-7 text-slate-600">
						Refresh the page to try again. If the problem continues, return to the
						Northern New Mexico College planning home page.
					</p>
					<div className="mt-7 flex flex-col justify-center gap-3 sm:flex-row">
						<button
							type="button"
							onClick={this.handleRetry}
							className="inline-flex min-h-12 items-center justify-center rounded-lg bg-blue-700 px-5 py-3 font-bold text-white transition hover:bg-blue-800 focus:outline-none focus-visible:ring-4 focus-visible:ring-blue-200"
						>
							Try Again
						</button>
						<a
							href="/NNMC"
							className="inline-flex min-h-12 items-center justify-center rounded-lg border border-slate-300 bg-white px-5 py-3 font-bold text-slate-800 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-4 focus-visible:ring-blue-200"
						>
							Return Home
						</a>
					</div>
				</section>
			</main>
		);
	}
}

export default AppErrorBoundary;
