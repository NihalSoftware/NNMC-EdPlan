import { useState } from "react";
import {
  NOT_REPORTED,
  admissionsMetrics,
  costMetrics,
  enrollmentMetrics,
  getMetricValue,
  hasValue,
  institutionMetrics,
  outcomeMetrics,
  overviewMetrics,
} from "./collegeMetrics.jsx";

const SectionCard = ({ title, children, note }) => (
  <div className="bg-white border border-slate-200 rounded-xl shadow-sm hover:shadow-lg p-5 space-y-3">
    <div>
      <h3 className="text-[20px] font-bold text-slate-700">{title}</h3>
      {note && <p className="text-xs text-slate-500">{note}</p>}
    </div>
    {children}
  </div>
);

const ComparisonTable = ({
  title,
  metrics,
  schools,
  note,
  collapsible = false,
}) => {
  const [open, setOpen] = useState(!collapsible);

  return (
    <SectionCard
      title={
        <button
          type="button"
          className="w-full text-left flex items-center justify-between"
          onClick={() => collapsible && setOpen((previous) => !previous)}
        >
          <span>{title}</span>
          {collapsible && (
            <span className="text-sm font-medium text-[#281ed5]">
              {open ? "Collapse" : "Expand"}
            </span>
          )}
        </button>
      }
      note={note}
    >
      {(!collapsible || open) && (
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <tbody>
              {metrics.map((metric) => (
                <tr
                  key={metric.key || metric.label}
                  className="border-t border-slate-100"
                >
                  <td className="px-3 py-2 font-medium text-slate-700 w-1/2">
                    {metric.label}
                  </td>
                  {schools.map((school) => {
                    const rawValue = getMetricValue(metric, school);
                    let content = NOT_REPORTED;

                    if (metric.render) {
                      content = metric.render(rawValue, school);
                    } else if (metric.format && hasValue(rawValue)) {
                      content = metric.format(rawValue, school);
                    } else if (hasValue(rawValue)) {
                      content = String(rawValue);
                    }

                    return (
                      <td
                        key={`${metric.key || metric.label}-${
                          school.unit_id || school.name
                        }`}
                        className="px-3 py-2 text-slate-800 w-1/2"
                      >
                        {content}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </SectionCard>
  );
};

const CollegeDetail = ({ college }) => {
  if (!college) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 text-sm text-slate-600">
        Northern New Mexico College details are not available yet.
      </div>
    );
  }

  const schools = [college];

  return (
    <section id="nnmc-college-details" aria-label="NNMC College Details" className="scroll-mt-6 space-y-4">
      <ComparisonTable
        title="Northern Overview"
        metrics={overviewMetrics}
        schools={schools}
      />
      <ComparisonTable
        title="Institution & Academic Profile"
        metrics={institutionMetrics}
        schools={schools}
        collapsible
      />
      <ComparisonTable
        title="Admissions & Student Success"
        metrics={admissionsMetrics}
        schools={schools}
        collapsible
      />
      <ComparisonTable
        title="Enrollment Breakdown"
        metrics={enrollmentMetrics}
        schools={schools}
        collapsible
      />
      <ComparisonTable
        title="Cost of Attendance"
        metrics={costMetrics}
        schools={schools}
        note="Net price is the average annual cost after grants and scholarships."
        collapsible
      />
      <ComparisonTable
        title="Financial Aid & Student Outcomes"
        metrics={outcomeMetrics}
        schools={schools}
        note="Debt, repayment, and earnings measures cover the applicable federally aided cohorts."
        collapsible
      />
    </section>
  );
};

export default CollegeDetail;
