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

export const rateFor = (label) => {
  if (label === "XX★") return 7.5;
  if (label === "XX+") return 4.5;
  if (label === "XX") return 3;
  return 2.4;
};

const SHOWCASE_BLUEPRINTS = [
  { label: "XX★", codename: "Ink Leviathan", windowCount: 6, totalCount: 48, dangerDaysLeft: 12.4 },
  { label: "XX+", codename: "Kraken Voltage", windowCount: 4, totalCount: 36, dangerDaysLeft: 2.6 },
  { label: "XX", codename: "Tri-Slosh Tempest", windowCount: 3, totalCount: 28, dangerDaysLeft: 0.45 },
  { label: "XS+", codename: "Charger Aurora", windowCount: 3, totalCount: 24, dangerDaysLeft: 0.12 },
  { label: "XS", codename: "Splat Pulse", windowCount: 3, totalCount: 22, dangerDaysLeft: -0.5 },
  { label: "XS-", codename: "Ink Echo", windowCount: 2, totalCount: 20 },
  { label: "XA+", codename: "Wave Breaker", windowCount: 2, totalCount: 18 },
  { label: "XA", codename: "Inkstream Nomad", windowCount: 1, totalCount: 15 },
  { label: "XA-", codename: "Suction Drift", windowCount: 1, totalCount: 12 },
  { label: "XB+", codename: "Splashdown Relay", windowCount: 0, totalCount: 10 },
  { label: "XB", codename: "Tide Rider", windowCount: null, totalCount: 7 },
  { label: "XB-", codename: "Reef Rookie", windowCount: null, totalCount: 5 },
];

const metricWithinGrade = (label) => {
  const index = DISPLAY_GRADE_SCALE.findIndex(([, targetLabel]) => targetLabel === label);
  if (index < 0) return 180; // fallback midpoint
  const [upper] = DISPLAY_GRADE_SCALE[index];
  const lower = index > 0 ? DISPLAY_GRADE_SCALE[index - 1][0] : Number.NEGATIVE_INFINITY;

  if (!Number.isFinite(upper)) {
    const base = Number.isFinite(lower) ? lower : 250;
    return base + 20;
  }

  if (!Number.isFinite(lower)) {
    return upper - 5;
  }

  const midpoint = lower + (upper - lower) * 0.65;
  return Math.min(upper - 0.5, Math.max(lower + 0.5, midpoint));
};

export const createGradeShowcaseRows = () =>
  SHOWCASE_BLUEPRINTS.map((blueprint, index) => {
    const metric = metricWithinGrade(blueprint.label);
    const displayScore = metric - 150;
    const playerId = `__sample_${blueprint.label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
    const displayName = `[Sample] ${blueprint.label} — ${blueprint.codename}`;

    return {
      player_id: playerId,
      display_name: displayName,
      stable_rank: null,
      display_score: displayScore,
      window_tournament_count: blueprint.windowCount ?? null,
      tournament_count: blueprint.totalCount ?? null,
      danger_days_left: blueprint.windowCount === 3 ? blueprint.dangerDaysLeft ?? null : null,
      is_showcase: true,
      showcase_order: index,
    };
  });
