import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import GeneratedSchedulesList from "../components/scheduling/GeneratedSchedulesList.jsx";
import WeeklyCalendar from "../components/scheduling/WeeklyCalendar.jsx";
import {
	activateGeneratedSchedule,
	getGeneratedSchedule,
	getGeneratedSchedules,
} from "../services/scheduleService.js";

const ScheduleGenerator = () => {
	const [searchParams, setSearchParams] = useSearchParams();
	const planIdFromQuery = searchParams.get("plan_id") || "";
	const [planIdInput, setPlanIdInput] = useState(planIdFromQuery);
	const [activePlanId, setActivePlanId] = useState(planIdFromQuery);
	const [schedules, setSchedules] = useState([]);
	const [selectedSchedule, setSelectedSchedule] = useState(null);
	const [loading, setLoading] = useState(false);
	const [loadingDetail, setLoadingDetail] = useState(false);
	const [activatingScheduleId, setActivatingScheduleId] = useState("");
	const [error, setError] = useState("");
	const [detailError, setDetailError] = useState("");

	const selectedScheduleId = selectedSchedule?.schedule_id || "";

	const selectedSectionCount = selectedSchedule?.sections?.length || 0;
	const pageMetrics = useMemo(
		() => [
			{ label: "Schedules", value: schedules.length },
			{ label: "Selected Sections", value: selectedSectionCount },
			{ label: "Credits", value: selectedSchedule?.total_credits ?? 0 },
			{
				label: "Meeting Hours",
				value: selectedSchedule?.total_meeting_hours ?? 0,
			},
		],
		[schedules.length, selectedSchedule, selectedSectionCount]
	);

	const loadSchedules = useCallback(async (planId) => {
		if (!planId) return;
		setLoading(true);
		setError("");
		setDetailError("");
		try {
			const data = await getGeneratedSchedules(planId);
			setSchedules(data);
			setSelectedSchedule(data[0] || null);
		} catch (err) {
			setSchedules([]);
			setSelectedSchedule(null);
			if (err.response?.status === 401) {
				setError("Please login again to view generated schedules.");
			} else if (err.response?.status === 404) {
				setError("This plan was not found for your account.");
			} else {
				setError("Unable to load generated schedules right now.");
			}
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		if (activePlanId) {
			loadSchedules(activePlanId);
		}
	}, [activePlanId, loadSchedules]);

	const handleSubmit = (event) => {
		event.preventDefault();
		const nextPlanId = planIdInput.trim();
		if (!nextPlanId) return;
		setSearchParams({ plan_id: nextPlanId });
		setActivePlanId(nextPlanId);
	};

	const handleSelectSchedule = async (schedule) => {
		if (!activePlanId || !schedule?.schedule_id) return;
		setSelectedSchedule(schedule);
		setLoadingDetail(true);
		setDetailError("");
		try {
			const detail = await getGeneratedSchedule(activePlanId, schedule.schedule_id);
			setSelectedSchedule(detail);
		} catch {
			setDetailError("Unable to load this schedule's full details.");
		} finally {
			setLoadingDetail(false);
		}
	};

	const handleActivateSchedule = async (schedule) => {
		if (!activePlanId || !schedule?.schedule_id) return;
		setActivatingScheduleId(schedule.schedule_id);
		setDetailError("");
		try {
			const activatedSchedule = await activateGeneratedSchedule(
				activePlanId,
				schedule.schedule_id
			);
			setSchedules((prev) =>
				prev.map((item) => {
					if (item.schedule_id === activatedSchedule.schedule_id) {
						return activatedSchedule;
					}
					return item.status === "Active"
						? { ...item, status: "Archived" }
						: item;
				})
			);
			setSelectedSchedule(activatedSchedule);
		} catch (err) {
			if (err.response?.status === 401) {
				setDetailError("Please login again to activate this schedule.");
			} else if (err.response?.status === 404) {
				setDetailError("This generated schedule was not found.");
			} else {
				setDetailError("Unable to activate this schedule right now.");
			}
		} finally {
			setActivatingScheduleId("");
		}
	};

	return (
		<section className="min-h-screen bg-slate-100 p-4 sm:p-6">
			<div className="mx-auto max-w-7xl space-y-6">
				<header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
					<div>
						<h1 className="text-3xl font-semibold text-slate-900">
							NNMC Schedule Generator
						</h1>
						<p className="mt-2 max-w-2xl text-sm text-slate-600">
							Inspect generated schedules for your Northern New Mexico College
							academic plan before choosing one.
						</p>
					</div>

					<form
						onSubmit={handleSubmit}
						className="flex w-full flex-col gap-2 sm:w-auto sm:min-w-[460px] sm:flex-row"
					>
						<input
							value={planIdInput}
							onChange={(event) => setPlanIdInput(event.target.value)}
							className="min-h-11 flex-1 rounded-md border border-slate-300 px-3 text-sm outline-none focus:border-[#016ce6] focus:ring-2 focus:ring-[#016ce6]/20"
							placeholder="Enter normalized plan ID"
						/>
						<button
							type="submit"
							className="min-h-11 rounded-md bg-[#016ce6] px-4 text-sm font-semibold text-white hover:bg-[#0059bd]"
						>
							Load
						</button>
					</form>
				</header>

				<div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
					{pageMetrics.map((metric) => (
						<div
							key={metric.label}
							className="rounded-lg border border-slate-200 bg-white p-4"
						>
							<p className="text-xs font-semibold uppercase text-slate-500">
								{metric.label}
							</p>
							<p className="mt-1 text-2xl font-semibold text-slate-900">
								{metric.value}
							</p>
						</div>
					))}
				</div>

				<div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
					<aside className="space-y-3">
						<div>
							<h2 className="text-lg font-semibold text-slate-900">
								Generated Schedules
							</h2>
							<p className="text-sm text-slate-500">
								Select a schedule to inspect its weekly layout.
							</p>
						</div>
						<GeneratedSchedulesList
							activatingScheduleId={activatingScheduleId}
							error={error}
							loading={loading}
							onActivateSchedule={handleActivateSchedule}
							onRetry={() => loadSchedules(activePlanId)}
							onSelectSchedule={handleSelectSchedule}
							schedules={schedules}
							selectedScheduleId={selectedScheduleId}
						/>
					</aside>

					<div className="space-y-3">
						{detailError && (
							<div className="rounded-lg border border-rose-100 bg-rose-50 px-4 py-3 text-sm text-rose-700">
								{detailError}
							</div>
						)}
						{loadingDetail && (
							<div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
								Loading schedule details...
							</div>
						)}
						{selectedSchedule ? (
							<WeeklyCalendar schedule={selectedSchedule} />
						) : (
							<div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-sm text-slate-600">
								Load a plan with generated schedules to view the calendar.
							</div>
						)}
					</div>
				</div>
			</div>
		</section>
	);
};

export default ScheduleGenerator;
