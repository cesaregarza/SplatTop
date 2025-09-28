export const CRACKLE_PURPLE = "#a78bfa";

export const nf2 = new Intl.NumberFormat(undefined, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const RAW_GRADE_SCALE = [
  [-5, "XB-"],
  [-4, "XB"],
  [-3, "XB+"],
  [-2, "XA-"],
  [-1, "XA"],
  [0, "XA+"],
  [0.8, "XS-"],
  [1.5, "XS"],
  [2.4, "XS+"],
  [4, "XX"],
  [5, "XX+"],
  [Infinity, "XX★"],
];

export const DISPLAY_GRADE_SCALE = RAW_GRADE_SCALE.map(([threshold, label]) => [
  threshold * 25 + 150,
  label,
]);

export const gradeFor = (displayValue) => {
  for (const [threshold, label] of DISPLAY_GRADE_SCALE) {
    if (displayValue <= threshold) return label;
  }
  return "—";
};

export const formatDate = (ms) => {
  if (!ms) return "—";
  const date = new Date(ms);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleDateString();
};

export const severityOf = (days) => {
  if (days == null) return "neutral";
  if (days < 0) return "expired";
  if (days <= 0.25) return "critical";
  if (days <= 1) return "warn";
  if (days <= 3) return "watch";
  return "ok";
};

export const chipClass = (severity) =>
  ({
    ok: "bg-emerald-500/10 text-emerald-200 ring-1 ring-emerald-400/15",
    watch: "bg-yellow-500/10 text-yellow-100 ring-1 ring-yellow-400/15",
    warn: "bg-amber-500/15 text-amber-200 ring-1 ring-amber-400/20",
    critical: "bg-rose-500/15 text-rose-300 ring-1 ring-rose-400/20",
    expired: "bg-rose-600/20 text-rose-200 ring-1 ring-rose-500/25",
    neutral: "bg-slate-700/20 text-slate-300 ring-1 ring-white/10",
  }[severity] || "bg-slate-700/20 text-slate-300 ring-1 ring-white/10");

export const tierFor = (label) => {
  switch (label) {
    case "XX★":
      return "grade-tier-xxstar";
    case "XX+":
      return "grade-tier-xxplus";
    case "XX":
      return "grade-tier-xx";
    case "XS+":
      return "grade-tier-xsplus";
    case "XS":
      return "grade-tier-xs";
    case "XS-":
      return "grade-tier-xsminus";
    case "XA+":
      return "grade-tier-xaplus";
    case "XA":
      return "grade-tier-xa";
    case "XA-":
      return "grade-tier-xaminus";
    case "XB+":
      return "grade-tier-xbplus";
    case "XB":
      return "grade-tier-xb";
    case "XB-":
      return "grade-tier-xbminus";
    default:
      return "grade-tier-default";
  }
};

export const gradeChipClass = (label, active) => {
  const tier = tierFor(label);
  return `grade-chip ${tier} ${active ? "is-active" : ""}`.trim();
};

export const isXX = (label) => label === "XX★" || label === "XX+" || label === "XX";

export const rateFor = (label) => (label === "XX★" ? 4 : label === "XX+" ? 3 : 2.4);
