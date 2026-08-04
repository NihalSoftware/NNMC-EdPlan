export const NOT_REPORTED = "Not reported by College Scorecard";

export const hasValue = (value) =>
  value !== undefined && value !== null && value !== "";

export const formatPercent = (value) =>
  hasValue(value)
    ? `${(Number(value) * 100).toFixed(1).replace(/\.0$/, "")} %`
    : NOT_REPORTED;

export const formatCurrency = (value) =>
  hasValue(value) ? `$${Number(value).toLocaleString()}` : NOT_REPORTED;

export const formatNumber = (value) =>
  hasValue(value) ? Number(value).toLocaleString() : NOT_REPORTED;

export const formatRatio = (value) =>
  hasValue(value) ? `${Number(value).toFixed(0)} : 1` : NOT_REPORTED;

const formatWebsite = (value) =>
  value ? (
    <a
      href={value.startsWith("http") ? value : `https://${value}`}
      target="_blank"
      rel="noreferrer"
      className="text-indigo-600 hover:text-indigo-500"
    >
      Visit Website
    </a>
  ) : (
    NOT_REPORTED
  );

const formatScoreRange = (low, high, school) => {
  if (hasValue(low) && hasValue(high)) {
    return `${formatNumber(low)} - ${formatNumber(high)}`;
  }
  if (hasValue(low)) return `>= ${formatNumber(low)}`;
  if (hasValue(high)) return `<= ${formatNumber(high)}`;
  return school?.open_admissions_policy
    ? "Not required (open admission)"
    : NOT_REPORTED;
};

const formatAdmissionRate = (value, school) => {
  if (hasValue(value)) return formatPercent(value);
  return school?.open_admissions_policy ? "Open admission" : NOT_REPORTED;
};

const formatCampusDesignation = (value) => {
  if (value === true) return "Main campus";
  if (value === false) return "Branch campus";
  return NOT_REPORTED;
};

export const overviewMetrics = [
  { key: "city", label: "City" },
  { key: "state", label: "State" },
  { key: "organization_type", label: "Institution Type" },
  { key: "location_type", label: "Campus Setting" },
  {
    key: "main_campus",
    label: "Campus Designation",
    format: formatCampusDesignation,
  },
  { key: "branch_count", label: "Reported Branches", format: formatNumber },
  { key: "size", label: "Undergraduate Enrollment", format: formatNumber },
  { key: "website", label: "Official Website", format: formatWebsite },
];

export const institutionMetrics = [
  { key: "accreditor", label: "Institutional Accreditor" },
  {
    key: "predominant_degree",
    label: "Predominant Undergraduate Award",
  },
  { key: "highest_degree", label: "Highest Degree Awarded" },
  {
    key: "student_faculty_ratio",
    label: "Student-to-Faculty Ratio",
    format: formatRatio,
  },
];

export const admissionsMetrics = [
  {
    key: "acceptance_rate",
    label: "Acceptance Rate",
    render: (value, school) => formatAdmissionRate(value, school),
  },
  { key: "graduation_rate", label: "Graduation Rate", format: formatPercent },
  {
    key: "first_year_return_rate",
    label: "First-Year Retention Rate",
    format: formatPercent,
  },
  {
    key: "sat_reading_range",
    label: "SAT Critical Reading Range",
    render: (_, school) =>
      formatScoreRange(
        school?.sat_reading_25th,
        school?.sat_reading_75th,
        school,
      ),
  },
  {
    key: "act_score_range",
    label: "ACT Score Range",
    render: (_, school) =>
      formatScoreRange(school?.act_score_25th, school?.act_score_75th, school),
  },
];

export const enrollmentMetrics = [
  { key: "size", label: "Undergraduate Enrollment", format: formatNumber },
  {
    key: "international_students",
    label: "International Students",
    format: formatNumber,
  },
  {
    key: "full_time_enrollment",
    label: "Full-Time Enrollment",
    format: formatNumber,
  },
  {
    key: "part_time_enrollment",
    label: "Part-Time Enrollment",
    format: formatNumber,
  },
];

export const costMetrics = [
  {
    key: "average_annual_cost",
    label: "Average Annual Net Fee",
    format: formatCurrency,
  },
  { key: "in_state_tuition", label: "In-State Tuition", format: formatCurrency },
  {
    key: "out_of_state_tuition",
    label: "Out-of-State Tuition",
    format: formatCurrency,
  },
  {
    key: "on_campus_room_and_board",
    label: "On-Campus Room and Board",
    format: formatCurrency,
  },
  {
    key: "books_and_supplies",
    label: "Books and Supplies",
    format: formatCurrency,
  },
];

export const outcomeMetrics = [
  {
    key: "median_earnings",
    label: "Median Earnings 10 Years After Entry",
    format: formatCurrency,
  },
  {
    key: "median_debt",
    label: "Median Debt After Graduation",
    format: formatCurrency,
  },
  {
    key: "typical_monthly_payment",
    label: "Estimated Monthly Loan Payment",
    format: formatCurrency,
  },
  {
    key: "federal_loan_rate",
    label: "Students Using Federal Loans",
    format: formatPercent,
  },
  {
    key: "pell_grant_rate",
    label: "Students Receiving Pell Grants",
    accessor: (school) => school.socioeconomic_diversity?.pell_grant_rate,
    format: formatPercent,
  },
  {
    key: "first_generation_share",
    label: "First-Generation Students",
    accessor: (school) =>
      school.socioeconomic_diversity?.first_generation_share,
    format: formatPercent,
  },
  {
    key: "repayment_rate",
    label: "Three-Year Loan Repayment Rate",
    format: formatPercent,
  },
  {
    key: "percent_more_than_hs",
    label: "Earning More Than a High School Graduate",
    format: formatPercent,
  },
];

export const getMetricValue = (metric, school) => {
  if (metric.accessor) return metric.accessor(school || {});
  return metric.key && school ? school[metric.key] : undefined;
};
