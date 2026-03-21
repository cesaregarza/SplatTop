import {
  DISPLAY_GRADE_SCALE,
  nf0,
} from "./stableLeaderboardUtils";

export const XX_PLUS_LABEL = "XX+";
export const XX_PLUS_THRESHOLD = 250;
export const HISTORY_PAGE_SIZE = 12;
const RECENT_EVENT_LIMIT = 5;
const MATCH_LOO_DISPLAY_SCALE = 25;
const MINUTE_MS = 60 * 1000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;

export const MATCH_RESULTS_TECHNICAL_NOTE =
  "Technical note: leave-one-out shortlist from this ranking run. Contribution is the negated score delta after removing one shortlisted match.";
export const EMPTY_TEXT_LIST = Object.freeze([]);
export const EMPTY_EXPANDED_ROWS = Object.freeze({});
export const MATCH_RESULT_VIEW_OPTIONS = Object.freeze([
  {
    id: "helpful",
    label: "Most helpful",
    tone: "emerald",
    emptyText: "No helpful matches made the shortlist.",
  },
  {
    id: "harmful",
    label: "Most harmful",
    tone: "rose",
    emptyText: "No harmful matches made the shortlist.",
  },
  {
    id: "swings",
    label: "Biggest swings",
    tone: "amber",
    emptyText: "No shortlisted match swings yet.",
  },
]);

const GRADE_INDEX_BY_LABEL = new Map(
  DISPLAY_GRADE_SCALE.map(([, label], index) => [label, index])
);

export const pickInitialMatchResultView = ({
  helpfulCount,
  harmfulCount,
  swingCount,
}) => {
  if (helpfulCount > 0) return "helpful";
  if (harmfulCount > 0) return "harmful";
  if (swingCount > 0) return "swings";
  return MATCH_RESULT_VIEW_OPTIONS[0].id;
};

export const formatUtcDateTime = (timestampMs) => {
  if (timestampMs == null) return "—";
  const date = new Date(Number(timestampMs));
  if (Number.isNaN(date.getTime())) return "—";
  return `${date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  })} UTC`;
};

export const describeDropStatus = (profile) => {
  const minRequired = Number(profile?.minimum_required_tournaments || 3);
  const rawWindowCount = profile?.window_tournament_count;
  const rawDaysLeft = profile?.danger_days_left;
  const windowCount =
    rawWindowCount == null ? null : Number(rawWindowCount);
  const daysLeft = rawDaysLeft == null ? null : Number(rawDaysLeft);

  if (Number.isFinite(daysLeft)) {
    if (daysLeft < 0) {
      return {
        label: "Inactive",
        className: "bg-rose-500/20 text-rose-100 ring-1 ring-rose-400/25",
      };
    }
    if (daysLeft < 1) {
      return {
        label: "Drops in <1d",
        className: "bg-amber-500/20 text-amber-100 ring-1 ring-amber-400/30",
      };
    }
    return {
      label: `Drops in ${Math.round(daysLeft)}d`,
      className: "bg-amber-500/20 text-amber-100 ring-1 ring-amber-400/30",
    };
  }

  if (Number.isFinite(windowCount) && windowCount >= minRequired) {
    const buffer = windowCount - minRequired;
    return {
      label: `Buffer +${buffer}`,
      className: "bg-emerald-500/20 text-emerald-100 ring-1 ring-emerald-400/25",
    };
  }

  return {
    label: "Not tracking",
    className: "bg-slate-700/30 text-slate-200 ring-1 ring-white/10",
  };
};

export const toSafeText = (value) => {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed || null;
};

export const toTextList = (value) => {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => toSafeText(String(item ?? "")))
    .filter(Boolean);
};

export const toComparisonKey = (value) => {
  const safe = toSafeText(String(value ?? ""));
  return safe ? safe.toLowerCase() : null;
};

export const toFiniteNumber = (value) => {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
};

const parseRecord = (value) => {
  const raw = toSafeText(value);
  if (!raw) return { wins: null, losses: null };
  const match = /^(\d+)\s*W\s*-\s*(\d+)\s*L$/i.exec(raw);
  if (!match) return { wins: null, losses: null };
  return {
    wins: Number(match[1]),
    losses: Number(match[2]),
  };
};

export const pluralize = (count, singular, plural = `${singular}s`) =>
  `${nf0.format(Math.max(0, Number(count) || 0))} ${
    Number(count) === 1 ? singular : plural
  }`;

export const formatRelativeAge = (timestampMs, referenceMs = Date.now()) => {
  const value = toFiniteNumber(timestampMs);
  const reference = toFiniteNumber(referenceMs) ?? Date.now();
  if (value == null) return "—";
  const diffMs = Math.max(0, reference - value);
  if (diffMs < HOUR_MS) {
    return `${Math.max(1, Math.round(diffMs / MINUTE_MS))}m ago`;
  }
  if (diffMs < 36 * HOUR_MS) {
    return `${Math.max(1, Math.round(diffMs / HOUR_MS))}h ago`;
  }
  if (diffMs < 60 * DAY_MS) {
    return `${Math.max(1, Math.round(diffMs / DAY_MS))}d ago`;
  }
  if (diffMs < 730 * DAY_MS) {
    return `${Math.max(1, Math.round(diffMs / (30 * DAY_MS)))}mo ago`;
  }
  return `${Math.max(1, Math.round(diffMs / (365 * DAY_MS)))}y ago`;
};

export const formatSignedNumber = (
  value,
  formatter,
  zeroLabel = "No change"
) => {
  const numeric = toFiniteNumber(value);
  if (numeric == null) return "—";
  if (Math.abs(numeric) < 0.01) return zeroLabel;
  return `${numeric > 0 ? "+" : "-"}${formatter.format(Math.abs(numeric))}`;
};

export const normalizeTournamentHistory = (rows) => {
  if (!Array.isArray(rows)) return [];

  const mapped = rows
    .map((row, index) => {
      const tournamentId = row?.tournament_id;
      const tournamentIdLabel =
        tournamentId == null ? null : String(tournamentId);
      const eventMs = toFiniteNumber(row?.event_ms);
      const tournamentName =
        toSafeText(row?.tournament_name) ||
        (tournamentIdLabel ? `Tournament ${tournamentIdLabel}` : "Tournament");
      const placementLabel = toSafeText(row?.placement_label);
      const resultSummary = toSafeText(row?.result_summary);
      const { wins, losses } = parseRecord(resultSummary);
      const matchesPlayed =
        wins != null && losses != null ? wins + losses : null;
      const outcome =
        wins == null || losses == null
          ? "unknown"
          : wins > losses
          ? "positive"
          : wins < losses
          ? "negative"
          : "even";
      const teamName = toSafeText(row?.team_name);
      const teamId =
        row?.team_id == null
          ? null
          : toSafeText(String(row.team_id)) || String(row.team_id);
      const eventDate = eventMs == null ? null : new Date(eventMs);
      const year =
        eventDate && !Number.isNaN(eventDate.getTime())
          ? String(eventDate.getUTCFullYear())
          : null;
      const key = `${tournamentIdLabel || "tournament"}:${eventMs || "na"}:${index}`;

      return {
        key,
        tournamentId: tournamentIdLabel,
        tournamentName,
        eventMs,
        placementLabel,
        resultSummary,
        wins,
        losses,
        matchesPlayed,
        outcome,
        teamName,
        teamId,
        year,
      };
    })
    .filter((row) => row.tournamentId || row.eventMs != null);

  mapped.sort((a, b) => {
    const delta = (b.eventMs ?? -1) - (a.eventMs ?? -1);
    if (delta !== 0) return delta;
    return String(b.tournamentId || "").localeCompare(
      String(a.tournamentId || "")
    );
  });

  return mapped;
};

export const normalizeMatchLooImpacts = (rows) => {
  if (!Array.isArray(rows)) return [];

  const mapped = rows
    .map((row, index) => {
      const matchId = row?.match_id == null ? null : String(row.match_id);
      const tournamentId =
        row?.tournament_id == null ? null : String(row.tournament_id);
      const eventMs = toFiniteNumber(row?.event_ms);
      const tournamentName =
        toSafeText(row?.tournament_name) ||
        (tournamentId ? `Tournament ${tournamentId}` : "Tournament");
      const exactScoreDelta = toFiniteNumber(row?.exact_score_delta);
      const exactAbsDeltaRaw = toFiniteNumber(row?.exact_abs_delta);
      const exactAbsDelta =
        exactAbsDeltaRaw ??
        (exactScoreDelta == null ? null : Math.abs(exactScoreDelta));
      const contributionDelta =
        exactScoreDelta == null
          ? null
          : exactScoreDelta * -1 * MATCH_LOO_DISPLAY_SCALE;
      const isWin =
        typeof row?.is_win === "boolean" ? row.is_win : null;
      const outcome =
        isWin == null ? "unknown" : isWin ? "positive" : "negative";
      const matchUrl =
        tournamentId && matchId
          ? `https://sendou.ink/to/${encodeURIComponent(
              tournamentId
            )}/matches/${encodeURIComponent(matchId)}`
          : null;

      return {
        key: `${matchId || "match"}:${tournamentId || "na"}:${index}`,
        matchId,
        tournamentId,
        tournamentName,
        eventMs,
        playerRank: toFiniteNumber(row?.player_rank),
        playerScore: toFiniteNumber(row?.player_score),
        isWin,
        outcome,
        exactScoreDelta,
        exactAbsDelta,
        contributionDelta,
        matchUrl,
        playerTeamName: toSafeText(row?.player_team_name),
        opponentTeamName: toSafeText(row?.opponent_team_name),
        playerTeamScore: toFiniteNumber(row?.player_team_score),
        opponentTeamScore: toFiniteNumber(row?.opponent_team_score),
        playerTeamPlayers: toTextList(row?.player_team_players),
        opponentTeamPlayers: toTextList(row?.opponent_team_players),
      };
    })
    .filter(
      (row) =>
        row.matchId ||
        row.tournamentId ||
        row.exactScoreDelta != null ||
        row.exactAbsDelta != null
    );

  mapped.sort((left, right) => {
    const delta = (right.exactAbsDelta ?? -1) - (left.exactAbsDelta ?? -1);
    if (delta !== 0) return delta;
    const eventDelta = (right.eventMs ?? -1) - (left.eventMs ?? -1);
    if (eventDelta !== 0) return eventDelta;
    return String(right.matchId || "").localeCompare(String(left.matchId || ""));
  });

  return mapped;
};

const pickDominantEntry = (map) => {
  let best = null;
  for (const entry of map.values()) {
    if (
      !best ||
      entry.count > best.count ||
      (entry.count === best.count &&
        entry.label.localeCompare(best.label, undefined, {
          sensitivity: "base",
        }) < 0)
    ) {
      best = entry;
    }
  }
  return best;
};

export const buildHistorySummary = (rows, referenceMs) => {
  let wins = 0;
  let losses = 0;
  let knownResults = 0;
  let positive = 0;
  let negative = 0;
  let even = 0;
  let unknown = 0;
  let totalMatches = 0;
  let placementNotes = 0;

  const teamCounts = new Map();
  const yearCounts = new Map();
  const eventMsValues = [];

  for (const row of rows) {
    if (row.wins != null && row.losses != null) {
      wins += row.wins;
      losses += row.losses;
      knownResults += 1;
      totalMatches += row.wins + row.losses;
    }

    if (row.outcome === "positive") positive += 1;
    else if (row.outcome === "negative") negative += 1;
    else if (row.outcome === "even") even += 1;
    else unknown += 1;

    if (row.placementLabel) placementNotes += 1;
    if (row.eventMs != null) eventMsValues.push(row.eventMs);

    const teamKey = row.teamId || row.teamName;
    if (teamKey) {
      const label = row.teamName || `Team ${row.teamId}`;
      const existing = teamCounts.get(teamKey);
      teamCounts.set(teamKey, {
        label,
        count: (existing?.count || 0) + 1,
      });
    }

    if (row.year) {
      const existing = yearCounts.get(row.year);
      yearCounts.set(row.year, {
        label: row.year,
        count: (existing?.count || 0) + 1,
      });
    }
  }

  let gapTotalMs = 0;
  let gapCount = 0;
  for (let index = 1; index < rows.length; index += 1) {
    const previousMs = rows[index - 1]?.eventMs;
    const currentMs = rows[index]?.eventMs;
    if (previousMs == null || currentMs == null) continue;
    gapTotalMs += Math.abs(previousMs - currentMs);
    gapCount += 1;
  }

  const latestMs = eventMsValues.length ? Math.max(...eventMsValues) : null;
  const firstMs = eventMsValues.length ? Math.min(...eventMsValues) : null;
  const reference = toFiniteNumber(referenceMs) ?? latestMs ?? Date.now();

  const countInWindow = (days) =>
    rows.filter((row) => {
      if (row.eventMs == null) return false;
      const delta = reference - row.eventMs;
      return delta >= 0 && delta <= days * DAY_MS;
    }).length;

  return {
    wins,
    losses,
    knownResults,
    positive,
    negative,
    even,
    unknown,
    uniqueTeams: teamCounts.size,
    uniqueYears: yearCounts.size,
    primaryTeam: pickDominantEntry(teamCounts),
    busiestYear: pickDominantEntry(yearCounts),
    placementNotes,
    totalMatches,
    averageMatches:
      knownResults > 0 ? totalMatches / knownResults : null,
    knownWinRate:
      wins + losses > 0 ? (wins / (wins + losses)) * 100 : null,
    knownCoveragePct:
      rows.length > 0 ? (knownResults / rows.length) * 100 : null,
    latestMs,
    firstMs,
    spanDays:
      latestMs != null && firstMs != null
        ? Math.max(0, (latestMs - firstMs) / DAY_MS)
        : null,
    cadenceDays:
      gapCount > 0 ? gapTotalMs / gapCount / DAY_MS : null,
    recent30Count: countInWindow(30),
    recent90Count: countInWindow(90),
    recent365Count: countInWindow(365),
    recentEvents: rows.slice(0, RECENT_EVENT_LIMIT),
  };
};

export const resolveCompetitionTrackTarget = (grade) => {
  if (grade === "XX+" || grade === "XX★") {
    return {
      label: XX_PLUS_LABEL,
      threshold: XX_PLUS_THRESHOLD,
      forceFull: true,
    };
  }

  const gradeIndex = GRADE_INDEX_BY_LABEL.get(grade);
  const currentThresholdEntry =
    gradeIndex != null ? DISPLAY_GRADE_SCALE[gradeIndex] : null;
  const nextThresholdEntry =
    gradeIndex != null && gradeIndex + 1 < DISPLAY_GRADE_SCALE.length
      ? DISPLAY_GRADE_SCALE[gradeIndex + 1]
      : null;

  if (!currentThresholdEntry || !nextThresholdEntry) {
    return {
      label: XX_PLUS_LABEL,
      threshold: XX_PLUS_THRESHOLD,
      forceFull: false,
    };
  }

  const [currentThreshold] = currentThresholdEntry;
  const [, nextLabel] = nextThresholdEntry;
  if (!Number.isFinite(currentThreshold) || nextLabel === "XX★") {
    return {
      label: XX_PLUS_LABEL,
      threshold: XX_PLUS_THRESHOLD,
      forceFull: true,
    };
  }

  return {
    label: nextLabel,
    threshold: Number(currentThreshold),
    forceFull: false,
  };
};
