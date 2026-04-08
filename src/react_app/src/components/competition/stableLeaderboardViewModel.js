import {
  CRACKLE_PURPLE,
  DISPLAY_GRADE_SCALE,
  chipClass,
  createGradeShowcaseRows,
  gradeFor,
  nf2,
  severityOf,
} from "./stableLeaderboardUtils";

const rawShowcaseFlag = process.env.REACT_APP_SHOWCASE_STABLE_LEADERBOARD;
const ENABLE_SHOWCASE_ROWS =
  rawShowcaseFlag != null
    ? String(rawShowcaseFlag).trim().toLowerCase() !== "false"
    : process.env.NODE_ENV !== "production";

export const SHOWCASE_ROWS = ENABLE_SHOWCASE_ROWS
  ? createGradeShowcaseRows()
  : [];

const mapLeaderboardRowWithGrade = (row) => {
  const baseDisplay = row.display_score ?? null;
  const shifted = baseDisplay == null ? null : baseDisplay + 150;
  const rawScore =
    row.stable_score !== undefined && row.stable_score !== null
      ? row.stable_score
      : row.score !== undefined && row.score !== null
      ? row.score
      : null;
  const gradeMetric =
    rawScore != null
      ? rawScore * 25 + 150
      : shifted != null
      ? shifted
      : null;
  const grade = gradeMetric == null ? "—" : gradeFor(gradeMetric);
  return { ...row, _shifted: shifted, _grade: grade };
};

const matchesStableLeaderboardQuery = (row, needle) =>
  row.display_name?.toLowerCase().includes(needle) ||
  String(row.player_id ?? "").toLowerCase().includes(needle);

export const prepareStableLeaderboardRows = ({
  rows,
  query,
  page,
  pageSize,
  gradeFilter,
  showcaseRows = SHOWCASE_ROWS,
}) => {
  const data = Array.isArray(rows) ? rows : [];
  const q = String(query || "").trim().toLowerCase();
  const mappedReal = data.map(mapLeaderboardRowWithGrade);
  const presentGrades = Array.from(
    new Set(
      mappedReal
        .map((row) => row._grade)
        .filter((value) => value && value !== "—")
    )
  );

  const filteredReal = q
    ? mappedReal.filter((row) => matchesStableLeaderboardQuery(row, q))
    : mappedReal.slice();

  filteredReal.sort(
    (a, b) => (a.stable_rank ?? Infinity) - (b.stable_rank ?? Infinity)
  );

  const gradeFilteredReal = gradeFilter
    ? filteredReal.filter((row) => row._grade === gradeFilter)
    : filteredReal;

  const total = gradeFilteredReal.length;
  const effectivePageCount = Math.max(1, Math.ceil(Math.max(total, 1) / pageSize));
  const current = Math.min(page, effectivePageCount);
  const start = (current - 1) * pageSize;
  const end = start + pageSize;
  const pageRows = gradeFilteredReal.slice(start, end);

  let filteredShowcase = [];
  let pageShowcase = [];
  if (!gradeFilter && showcaseRows.length) {
    const mappedShowcase = showcaseRows.map(mapLeaderboardRowWithGrade);
    filteredShowcase = q
      ? mappedShowcase.filter((row) => matchesStableLeaderboardQuery(row, q))
      : mappedShowcase.slice();
    filteredShowcase.sort((a, b) => {
      const orderA = a.showcase_order ?? Number.MAX_SAFE_INTEGER;
      const orderB = b.showcase_order ?? Number.MAX_SAFE_INTEGER;
      return orderA - orderB;
    });
    pageShowcase = current === 1 ? filteredShowcase : [];
  }

  return {
    filtered: [...pageRows, ...pageShowcase],
    total,
    pageCount: effectivePageCount,
    current,
    all: [...gradeFilteredReal, ...filteredShowcase],
    hasShowcase: filteredShowcase.length > 0,
    pageRealCount: pageRows.length,
    availableGrades: presentGrades,
  };
};

export const getVisibleStableLeaderboardGrades = (availableGrades) => {
  const present = new Set(availableGrades || []);
  return DISPLAY_GRADE_SCALE.map(([, label]) => label)
    .slice()
    .reverse()
    .filter((label) => present.has(label));
};

export const buildStableLeaderboardRowView = (row, highlightId) => {
  const rank = row.stable_rank ?? "—";
  const grade = row._grade;
  const rankScore = row._shifted ?? null;
  const windowCount = row.window_tournament_count ?? null;
  const totalTournaments = row.tournament_count ?? null;
  const hasDangerMetric = row.danger_days_left != null;
  const days = hasDangerMetric ? row.danger_days_left : null;
  const hasBaseline = Boolean(row.delta_has_baseline);
  const rankDeltaRaw = hasBaseline ? row.rank_delta : null;
  const displayScoreDelta = hasBaseline ? row.display_score_delta : null;
  const isNewEntry = hasBaseline ? Boolean(row.delta_is_new) : false;

  let windowCountClass = "text-slate-200";
  if (windowCount === 3) {
    windowCountClass = "text-rose-400";
  } else if (windowCount != null && windowCount < 6) {
    windowCountClass = "text-amber-200";
  }

  let severity = "neutral";
  let daysLabel = "Not tracking";
  let daysTitle =
    "We do not yet track inactivity risk for this player in the current window.";

  if (days != null) {
    severity = severityOf(days);
    if (days < 0) {
      daysLabel = "Inactive";
      daysTitle =
        "The player's ranked activity window has expired. They will drop until they play another ranked event.";
    } else if (days < 1) {
      daysLabel = "<1d";
      daysTitle =
        "Less than one day remains before this player becomes inactive.";
    } else {
      const rounded = Math.round(days);
      daysLabel = `${rounded}d`;
      daysTitle = `${rounded} day${
        rounded === 1 ? "" : "s"
      } until this player becomes inactive without a new ranked event.`;
    }
  } else if (windowCount != null && windowCount >= 3) {
    severity = "ok";
    daysLabel = "OK";
    daysTitle =
      "Player meets the ranked activity requirement; countdown resumes when they fall back to three events in the 120 day window.";
  } else if (windowCount == null || windowCount < 3) {
    daysLabel = "Not tracking";
    daysTitle =
      "Fewer than three ranked tournaments in the current window, so inactivity countdown is not tracked yet.";
  }

  const chipClassName = chipClass(severity);
  const rankScoreClass =
    rankScore == null
      ? "text-slate-100"
      : rankScore >= 300
      ? "text-amber-100"
      : rankScore >= 250
      ? "text-fuchsia-200"
      : "text-slate-100";

  const scoreClasses = [
    "font-semibold",
    rankScoreClass,
    "font-data",
    "tabular-nums",
  ];
  const scoreDataProps = {};
  const showScoreHighlight = grade === "XX★";
  if (showScoreHighlight) {
    scoreClasses.push("xxstar-score", "crackle");
    scoreDataProps["data-color"] = CRACKLE_PURPLE;
    scoreDataProps["data-rate"] = 9;
  }

  const scoreTitle =
    rankScore == null
      ? "Rank score not available for this player yet."
      : `Rank score ${nf2.format(rankScore)}. Higher scores indicate stronger recent performance.`;

  const highlighted = Boolean(highlightId && row.player_id === highlightId);
  const highlightClass = highlighted
    ? "ring-2 ring-fuchsia-500/40 ring-offset-0"
    : "";

  let rankChangeLabel = null;
  let rankChangeClass = "";
  let rankChangeTitle = "";
  if (hasBaseline) {
    if (isNewEntry) {
      rankChangeLabel = "NEW";
      rankChangeClass = "text-emerald-300";
      rankChangeTitle = "New entrant compared to the previous snapshot.";
    } else if (Number.isFinite(rankDeltaRaw) && rankDeltaRaw !== 0) {
      const improved = rankDeltaRaw > 0;
      const prefix = improved ? "+" : "";
      rankChangeLabel = `${prefix}${rankDeltaRaw}`;
      rankChangeClass = improved ? "text-emerald-300" : "text-rose-300";
      rankChangeTitle = improved
        ? "Rank has improved since the previous snapshot."
        : "Rank has fallen since the previous snapshot.";
    }
  }

  let scoreChangeLabel = null;
  let scoreChangeClass = "";
  let scoreChangeTitle = "";
  if (hasBaseline && !isNewEntry && Number.isFinite(displayScoreDelta)) {
    if (Math.abs(displayScoreDelta) >= 0.01) {
      const improved = displayScoreDelta > 0;
      const prefix = improved ? "+" : "-";
      const magnitude = nf2.format(Math.abs(displayScoreDelta));
      scoreChangeLabel = `${prefix}${magnitude}`;
      scoreChangeClass = improved ? "text-emerald-300" : "text-rose-300";
      scoreChangeTitle = improved
        ? "Rank score has increased since the previous snapshot."
        : "Rank score has decreased since the previous snapshot.";
    }
  }

  return {
    row,
    rank,
    grade,
    rankScore,
    rankScoreDisplay: rankScore == null ? "—" : nf2.format(rankScore),
    scoreClassName: scoreClasses.join(" "),
    scoreDataProps,
    barHighlightClass: showScoreHighlight ? "xxstar-scorebar" : "",
    chipClassName,
    daysLabel,
    daysTitle,
    windowCount,
    windowCountClass,
    totalTournaments,
    highlighted,
    highlightClass,
    scoreTitle,
    rankChangeLabel,
    rankChangeClass,
    rankChangeTitle,
    scoreChangeLabel,
    scoreChangeClass,
    scoreChangeTitle,
  };
};
