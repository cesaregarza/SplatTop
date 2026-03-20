import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Link, useParams } from "react-router-dom";
import useCompetitionPlayer from "../../hooks/useCompetitionPlayer";
import useCrackleEffect from "../../hooks/useCrackleEffect";
import {
  CRACKLE_PURPLE,
  DISPLAY_GRADE_SCALE,
  gradeFor,
  nf0,
  nf2,
  tierFor,
} from "./stableLeaderboardUtils";
import CompetitionLayout from "./CompetitionLayout";
import "./StableLeaderboardView.css";
import "./CompetitionPlayerPage.css";

const XX_PLUS_LABEL = "XX+";
const XX_PLUS_THRESHOLD = 250;
const HISTORY_PAGE_SIZE = 12;
const RECENT_EVENT_LIMIT = 5;
const RECENT_FORM_LIMIT = 6;
const MINUTE_MS = 60 * 1000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;
const MATCH_RESULTS_TECHNICAL_NOTE =
  "Technical note: leave-one-out shortlist from this ranking run. Contribution is the negated score delta after removing one shortlisted match.";
const EMPTY_TEXT_LIST = Object.freeze([]);
const MATCH_RESULT_VIEW_OPTIONS = Object.freeze([
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

const formatUtcDateTime = (timestampMs) => {
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

const formatUtcDate = (timestampMs) => {
  if (timestampMs == null) return "—";
  const date = new Date(Number(timestampMs));
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    timeZone: "UTC",
  });
};

const describeDropStatus = (profile) => {
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

const toSafeText = (value) => {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed || null;
};

const toTextList = (value) => {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => toSafeText(String(item ?? "")))
    .filter(Boolean);
};

const toComparisonKey = (value) => {
  const safe = toSafeText(String(value ?? ""));
  return safe ? safe.toLowerCase() : null;
};

const toFiniteNumber = (value) => {
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

const pluralize = (count, singular, plural = `${singular}s`) =>
  `${nf0.format(Math.max(0, Number(count) || 0))} ${
    Number(count) === 1 ? singular : plural
  }`;

const formatRelativeAge = (timestampMs, referenceMs = Date.now()) => {
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

const formatCompactSpan = (days) => {
  const numeric = toFiniteNumber(days);
  if (numeric == null) return "—";
  if (numeric < 1) {
    return `${Math.max(1, Math.round(numeric * 24))}h`;
  }
  if (numeric < 60) {
    return `${Math.max(1, Math.round(numeric))}d`;
  }
  if (numeric < 730) {
    return `${Math.max(1, Math.round(numeric / 30))}mo`;
  }
  return `${Math.max(1, Math.round(numeric / 365))}y`;
};

const formatSignedNumber = (value, formatter, zeroLabel = "No change") => {
  const numeric = toFiniteNumber(value);
  if (numeric == null) return "—";
  if (Math.abs(numeric) < 0.01) return zeroLabel;
  return `${numeric > 0 ? "+" : "-"}${formatter.format(Math.abs(numeric))}`;
};

const normalizeTournamentHistory = (rows) => {
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

const normalizeMatchLooImpacts = (rows) => {
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
        exactScoreDelta == null ? null : exactScoreDelta * -1;
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

const buildHistorySummary = (rows, referenceMs) => {
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
    recentForm: rows.slice(0, RECENT_FORM_LIMIT).map((row) => ({
      key: row.key,
      outcome: row.outcome,
      label: row.resultSummary || row.placementLabel || "Unknown result",
      secondary: formatUtcDate(row.eventMs),
    })),
  };
};

const buildSnapshotText = ({
  profile,
  grade,
  rankScore,
  minimumRequired,
  lifetimeRanked,
}) => {
  const name = profile?.display_name || "Unknown player";
  const id = profile?.player_id || "unknown";
  const hasLifetimeUnlock = lifetimeRanked >= minimumRequired;
  const hasVisibleRank =
    hasLifetimeUnlock && profile?.stable_rank != null;
  const hasVisibleScore = hasLifetimeUnlock && rankScore != null;
  const statusLabel = profile?.eligible
    ? "Live snapshot"
    : hasLifetimeUnlock
    ? "Not currently eligible"
    : "Unlocking profile";
  const rankLabel = hasVisibleRank
    ? `#${nf0.format(Number(profile.stable_rank))}`
    : "Hidden";
  const scoreLabel = hasVisibleScore
    ? `${nf2.format(rankScore)} / ${XX_PLUS_THRESHOLD}`
    : "Hidden";
  const tournamentsLabel = `${nf0.format(
    Number(profile?.window_tournament_count || 0)
  )} / ${nf0.format(lifetimeRanked)}`;

  return [
    `${name} (${id})`,
    `Status: ${statusLabel}`,
    `Rank: ${rankLabel}`,
    `Grade: ${hasVisibleScore ? grade : "Hidden"}`,
    `Rank score: ${scoreLabel}`,
    `Tournaments (120d/lifetime): ${tournamentsLabel}`,
    `Last tournament: ${formatUtcDateTime(profile?.last_tournament_ms)}`,
    `Snapshot updated: ${formatUtcDateTime(profile?.generated_at_ms)}`,
  ].join("\n");
};

const copyTextToClipboard = async (text) => {
  if (!text) return false;

  if (
    typeof navigator !== "undefined" &&
    navigator.clipboard?.writeText
  ) {
    await navigator.clipboard.writeText(text);
    return true;
  }

  if (typeof document === "undefined" || !document.body) return false;

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "true");
  textarea.style.position = "absolute";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  document.body.removeChild(textarea);
  return copied;
};

const GradeBadge = ({ label }) => {
  if (!label || label === "—") {
    return (
      <span className="grade-badge grade-tier-default" aria-label="No grade">
        —
      </span>
    );
  }

  const tier = tierFor(label);

  return (
    <span
      className={`grade-badge ${tier}`.trim()}
      title={`Grade ${label}`}
      aria-label={`Grade ${label}`}
    >
      {label}
    </span>
  );
};

const toneForTrackTarget = (label) => {
  switch (tierFor(label)) {
    case "grade-tier-xxstar":
    case "grade-tier-xxplus":
    case "grade-tier-xx":
      return "amber";
    case "grade-tier-xsplus":
    case "grade-tier-xs":
    case "grade-tier-xsminus":
      return "violet";
    case "grade-tier-xaplus":
    case "grade-tier-xa":
    case "grade-tier-xaminus":
      return "cyan";
    default:
      return "slate";
  }
};

const HeroStat = ({ label, value, detail, tone = "slate" }) => (
  <article
    className={`comp-player-hero-stat is-${tone}`.trim()}
    aria-label={label}
  >
    <p className="comp-player-hero-stat-value">{value}</p>
    <p className="comp-player-hero-stat-detail">
      <span className="comp-player-inline-label">{label}</span>
      {detail ? ` · ${detail}` : ""}
    </p>
  </article>
);

const FactChip = ({ label, value, tone = "slate" }) => (
  <div className={`comp-player-fact-chip is-${tone}`.trim()} aria-label={label}>
    <p className="comp-player-fact-value">
      <span className="comp-player-inline-label">{label}: </span>
      {value}
    </p>
  </div>
);

const InsightChip = ({ label, value, tone = "slate" }) => (
  <div
    className={`comp-player-insight-chip is-${tone}`.trim()}
    aria-label={label}
  >
    <p className="comp-player-insight-value font-data">
      <span className="comp-player-inline-label">{label}: </span>
      {value}
    </p>
  </div>
);

const SummaryCard = ({ value, title, detail, tone = "slate" }) => (
  <article className={`comp-player-summary-card is-${tone}`.trim()}>
    <p className="comp-player-summary-value">{value}</p>
    <p className="comp-player-summary-title">{title}</p>
    {detail ? <p className="comp-player-summary-detail">{detail}</p> : null}
  </article>
);

const FormPill = ({ entry }) => {
  const outcomeLabel =
    entry.outcome === "positive"
      ? "W"
      : entry.outcome === "negative"
      ? "L"
      : entry.outcome === "even"
      ? "="
      : "?";

  return (
    <div
      className={`comp-player-form-pill is-${entry.outcome}`.trim()}
      title={`${entry.secondary} · ${entry.label}`}
    >
      <span className="comp-player-form-pill-mark">{outcomeLabel}</span>
      <span className="comp-player-form-pill-date">{entry.secondary}</span>
    </div>
  );
};

const RecentEventCard = ({ row, referenceMs }) => {
  const stateLabel =
    row.outcome === "positive"
      ? "Positive"
      : row.outcome === "negative"
      ? "Negative"
      : row.outcome === "even"
      ? "Even"
      : "Unknown";
  const resultLabel =
    row.resultSummary || row.placementLabel || "Result not logged";

  return (
    <article className={`comp-player-recent-card is-${row.outcome}`.trim()}>
      <div className="comp-player-recent-head">
        <p className="comp-player-recent-age">
          {formatRelativeAge(row.eventMs, referenceMs)}
        </p>
        <span className={`comp-player-result-pill is-${row.outcome}`.trim()}>
          {stateLabel}
        </span>
      </div>
      <p className="comp-player-recent-title">{row.tournamentName}</p>
      <p className="comp-player-recent-meta">{formatUtcDate(row.eventMs)}</p>
      <p className="comp-player-recent-team">{row.teamName || "Unknown team"}</p>
      <p className="comp-player-recent-result font-data">{resultLabel}</p>
    </article>
  );
};

const MatchImpactRosterLine = ({
  label,
  players,
  highlightedPlayerNames = EMPTY_TEXT_LIST,
}) => {
  const highlightedKeys = new Set(
    highlightedPlayerNames
      .map((name) => toComparisonKey(name))
      .filter(Boolean)
  );
  const entries = players.length ? players : ["Players unavailable"];

  return (
    <div className="comp-player-impact-roster-line">
      <span className="comp-player-impact-roster-team">{label}:</span>
      <div className="comp-player-impact-roster-values">
        {entries.map((name, index) => {
          const isCurrent = highlightedKeys.has(toComparisonKey(name));
          const Tag = isCurrent ? "strong" : "span";
          return (
            <React.Fragment key={`${label}:${name}`}>
              <Tag
                className={`comp-player-impact-roster-name${
                  isCurrent ? " is-current" : ""
                }`.trim()}
              >
                {name}
              </Tag>
              {index < entries.length - 1 ? (
                <span className="comp-player-impact-roster-separator">, </span>
              ) : null}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

const toneForMatchImpact = (row) => {
  if ((row?.contributionDelta ?? 0) > 0) return "emerald";
  if ((row?.contributionDelta ?? 0) < 0) return "rose";
  return "amber";
};

const MatchImpactRow = ({
  row,
  referenceMs,
  highlightedPlayerNames = EMPTY_TEXT_LIST,
  showDirection = false,
}) => {
  const tone = toneForMatchImpact(row);
  const winLabel =
    row.isWin == null ? "Unknown result" : row.isWin ? "Win" : "Loss";
  const contribution = formatSignedNumber(
    row.contributionDelta,
    nf2,
    nf2.format(0)
  );
  const eventLabel =
    row.eventMs == null
      ? "Date unavailable"
      : `${formatUtcDate(row.eventMs)} · ${formatRelativeAge(
          row.eventMs,
          referenceMs
        )}`;
  const playerTeamLabel = row.playerTeamName || "Unknown team";
  const opponentTeamLabel = row.opponentTeamName || "Unknown opponent";
  const matchupLabel =
    row.playerTeamName || row.opponentTeamName
      ? `${playerTeamLabel} vs ${opponentTeamLabel}`
      : "Teams unavailable";
  const finalScoreLabel =
    row.playerTeamScore != null && row.opponentTeamScore != null
      ? `Final ${nf0.format(row.playerTeamScore)}-${nf0.format(
          row.opponentTeamScore
        )}`
      : "Final score unavailable";
  const directionLabel =
    (row.contributionDelta ?? 0) > 0
      ? "Helpful"
      : (row.contributionDelta ?? 0) < 0
      ? "Harmful"
      : "Even";
  const rowBody = (
    <>
      <div className="comp-player-impact-row-event">
        <p className="comp-player-impact-row-title">{row.tournamentName}</p>
        <p className="comp-player-impact-row-meta">{eventLabel}</p>
      </div>
      <div className="comp-player-impact-row-result">
        <div className="comp-player-impact-row-matchup">
          <p className="comp-player-impact-row-matchup-text">{matchupLabel}</p>
          <p className="comp-player-impact-row-score">
            <span
              className={`comp-player-impact-score-dot is-${row.outcome}`.trim()}
              aria-hidden="true"
            />
            <span>{finalScoreLabel}</span>
            <span className="comp-player-impact-row-score-state">{winLabel}</span>
          </p>
        </div>
        <MatchImpactRosterLine
          label={playerTeamLabel}
          players={row.playerTeamPlayers}
          highlightedPlayerNames={highlightedPlayerNames}
        />
        <MatchImpactRosterLine
          label={opponentTeamLabel}
          players={row.opponentTeamPlayers}
          highlightedPlayerNames={highlightedPlayerNames}
        />
      </div>
      <div className="comp-player-impact-row-summary">
        <p className="comp-player-impact-row-delta font-data">{contribution}</p>
        {showDirection ? (
          <p
            className={`comp-player-impact-row-direction is-${tone}`.trim()}
          >
            {directionLabel}
          </p>
        ) : null}
      </div>
    </>
  );

  if (row.matchUrl) {
    return (
      <a
        className={`comp-player-impact-row is-${tone}`.trim()}
        href={row.matchUrl}
        rel="noreferrer"
        target="_blank"
      >
        {rowBody}
      </a>
    );
  }

  return (
    <article className={`comp-player-impact-row is-${tone}`.trim()}>
      {rowBody}
    </article>
  );
};

const MatchImpactTable = ({
  rows,
  emptyText,
  referenceMs,
  highlightedPlayerNames,
  showDirection = false,
}) => {
  return (
    rows.length ? (
      <div className="comp-player-impact-table">
        <div className="comp-player-impact-table-head">
          <p>Event</p>
          <p>Result</p>
          <p>Contribution</p>
        </div>
        <div className="comp-player-impact-table-body">
          {rows.map((row) => (
            <MatchImpactRow
              key={row.key}
              row={row}
              referenceMs={referenceMs}
              highlightedPlayerNames={highlightedPlayerNames}
              showDirection={showDirection}
            />
          ))}
        </div>
      </div>
    ) : (
      <p className="comp-player-empty-text">{emptyText}</p>
    )
  );
};

const PulseRow = ({ label, value, detail }) => (
  <div className="comp-player-pulse-row">
    <div className="comp-player-pulse-copy">
      <p className="comp-player-pulse-label">{label}</p>
      {detail ? <p className="comp-player-pulse-detail">{detail}</p> : null}
    </div>
    <p className="comp-player-pulse-value">{value}</p>
  </div>
);

const CompetitionPlayerPage = ({ top500Href }) => {
  const { playerId } = useParams();
  const rootRef = useRef(null);
  const [historyQuery, setHistoryQuery] = useState("");
  const [historyYear, setHistoryYear] = useState("all");
  const [historyOutcome, setHistoryOutcome] = useState("all");
  const [historySort, setHistorySort] = useState("recent");
  const [pageState, setPageState] = useState({
    history: 1,
    resultsView: MATCH_RESULT_VIEW_OPTIONS[0].id,
  });
  const [shareStatus, setShareStatus] = useState(null);
  const { loading, error, profile, refresh } = useCompetitionPlayer(playerId);

  useEffect(() => {
    const previous = document.title;
    if (!profile) {
      document.title = "Competition - splat.top";
      return () => {
        document.title = previous;
      };
    }
    const displayName = profile.display_name || profile.player_id || "Player";
    document.title = `${displayName} - Competition - splat.top`;
    return () => {
      document.title = previous;
    };
  }, [profile]);

  const minimumRequired = Number(profile?.minimum_required_tournaments || 3);
  const lifetimeRanked = Number(profile?.lifetime_ranked_tournaments || 0);
  const hasLifetimeUnlock = lifetimeRanked >= minimumRequired;
  const rankScore =
    profile?.display_score == null ? null : Number(profile.display_score) + 150;
  const previousRankScore =
    profile?.previous_display_score == null
      ? null
      : Number(profile.previous_display_score) + 150;
  const hasVisibleRank =
    hasLifetimeUnlock && profile?.stable_rank != null;
  const hasVisibleScore =
    hasLifetimeUnlock && rankScore != null;
  const grade = hasVisibleScore ? gradeFor(rankScore) : "—";
  const heroHasLightning = Boolean(
    hasVisibleScore && (grade === "XX+" || grade === "XX★")
  );
  const trackTarget = useMemo(() => {
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
  }, [grade]);
  const scoreDeltaToThreshold =
    rankScore == null ? null : rankScore - trackTarget.threshold;
  const scoreProgressPct =
    rankScore == null
      ? 0
      : trackTarget.forceFull
      ? 100
      : Math.max(0, Math.min((rankScore / trackTarget.threshold) * 100, 100));
  const scoreTrackClass =
    rankScore != null && rankScore >= XX_PLUS_THRESHOLD
      ? "comp-player-score-fill is-threshold"
      : "comp-player-score-fill";
  const scoreTrackTone = toneForTrackTarget(trackTarget.label);
  const scoreHasLightning =
    rankScore != null && (rankScore >= XX_PLUS_THRESHOLD || grade === "XX★");
  const scoreHint =
    rankScore == null
      ? "Score hidden until eligible"
      : scoreDeltaToThreshold >= 0
      ? `${nf2.format(scoreDeltaToThreshold)} above ${trackTarget.label} threshold`
      : `${nf2.format(Math.abs(scoreDeltaToThreshold))} below ${trackTarget.label} threshold`;
  const progress = profile?.progress_to_minimum || {
    current: Math.min(lifetimeRanked, minimumRequired),
    required: minimumRequired,
    remaining: Math.max(0, minimumRequired - lifetimeRanked),
  };
  const progressPct = Math.max(
    0,
    Math.min(
      100,
      (Number(progress.current || 0) / Number(progress.required || 1)) * 100
    )
  );
  const dropStatus = useMemo(() => describeDropStatus(profile), [profile]);
  const tournamentHistory = useMemo(
    () => normalizeTournamentHistory(profile?.tournament_history_ranked),
    [profile?.tournament_history_ranked]
  );
  const historyYears = useMemo(
    () =>
      Array.from(
        new Set(tournamentHistory.map((row) => row.year).filter(Boolean))
      ).sort((a, b) => Number(b) - Number(a)),
    [tournamentHistory]
  );
  const historyGeneratedAtMs =
    profile?.history_generated_at_ms ?? profile?.generated_at_ms;
  const historyReferenceMs =
    toFiniteNumber(historyGeneratedAtMs) ?? Date.now();
  const historySummary = useMemo(
    () => buildHistorySummary(tournamentHistory, historyReferenceMs),
    [tournamentHistory, historyReferenceMs]
  );
  const matchLooImpacts = useMemo(
    () => normalizeMatchLooImpacts(profile?.match_loo_impacts),
    [profile?.match_loo_impacts]
  );
  const matchImpactHighlightedPlayerNames = useMemo(
    () =>
      Array.from(
        new Set(
          [profile?.display_name, profile?.player_id]
            .map((value) => toSafeText(String(value ?? "")))
            .filter(Boolean)
        )
      ),
    [profile?.display_name, profile?.player_id]
  );
  const matchLooCount =
    toFiniteNumber(profile?.match_loo_record_count) ?? matchLooImpacts.length;
  const harmfulMatchImpacts = useMemo(
    () =>
      matchLooImpacts
        .filter((row) => (row.exactScoreDelta ?? 0) > 0)
        .sort((left, right) => {
          const delta =
            (right.exactScoreDelta ?? -Infinity) -
            (left.exactScoreDelta ?? -Infinity);
          if (delta !== 0) return delta;
          return (right.exactAbsDelta ?? -1) - (left.exactAbsDelta ?? -1);
        }),
    [matchLooImpacts]
  );
  const helpfulMatchImpacts = useMemo(
    () =>
      matchLooImpacts
        .filter((row) => (row.exactScoreDelta ?? 0) < 0)
        .sort((left, right) => {
          const delta =
            (left.exactScoreDelta ?? Infinity) -
            (right.exactScoreDelta ?? Infinity);
          if (delta !== 0) return delta;
          return (right.exactAbsDelta ?? -1) - (left.exactAbsDelta ?? -1);
        }),
    [matchLooImpacts]
  );
  const swingMatchImpacts = matchLooImpacts;
  const hasMatchImpactPanel =
    profile?.match_loo_record_count != null || matchLooImpacts.length > 0;
  const filteredHistory = useMemo(() => {
    const query = historyQuery.trim().toLowerCase();
    const filtered = tournamentHistory.filter((row) => {
      if (historyYear !== "all" && row.year !== historyYear) return false;
      if (historyOutcome !== "all" && row.outcome !== historyOutcome) {
        return false;
      }
      if (!query) return true;

      return (
        row.tournamentName?.toLowerCase().includes(query) ||
        row.teamName?.toLowerCase().includes(query) ||
        String(row.tournamentId || "").toLowerCase().includes(query) ||
        String(row.teamId || "").toLowerCase().includes(query)
      );
    });

    filtered.sort((left, right) => {
      if (historySort === "oldest") {
        const delta = (left.eventMs ?? Infinity) - (right.eventMs ?? Infinity);
        if (delta !== 0) return delta;
        return String(left.tournamentId || "").localeCompare(
          String(right.tournamentId || "")
        );
      }
      if (historySort === "most_matches") {
        const delta =
          (right.matchesPlayed ?? -1) - (left.matchesPlayed ?? -1);
        if (delta !== 0) return delta;
      }
      const delta = (right.eventMs ?? -1) - (left.eventMs ?? -1);
      if (delta !== 0) return delta;
      return String(right.tournamentId || "").localeCompare(
        String(left.tournamentId || "")
      );
    });

    return filtered;
  }, [tournamentHistory, historyQuery, historyYear, historyOutcome, historySort]);
  const historyPageCount = Math.max(
    1,
    Math.ceil(filteredHistory.length / HISTORY_PAGE_SIZE)
  );
  const safeHistoryPage = Math.min(pageState.history, historyPageCount);
  const historyRows = useMemo(() => {
    const start = (safeHistoryPage - 1) * HISTORY_PAGE_SIZE;
    return filteredHistory.slice(start, start + HISTORY_PAGE_SIZE);
  }, [filteredHistory, safeHistoryPage]);
  const historyCount =
    toFiniteNumber(profile?.history_record_count) ?? tournamentHistory.length;
  const strongestHarmfulImpact = harmfulMatchImpacts[0] || null;
  const strongestHelpfulImpact = helpfulMatchImpacts[0] || null;
  const activeMatchImpactView =
    MATCH_RESULT_VIEW_OPTIONS.find(
      (option) => option.id === pageState.resultsView
    ) || MATCH_RESULT_VIEW_OPTIONS[0];
  const activeMatchImpactRows =
    activeMatchImpactView.id === "harmful"
      ? harmfulMatchImpacts
      : activeMatchImpactView.id === "swings"
      ? swingMatchImpacts
      : helpfulMatchImpacts;
  useEffect(() => {
    setPageState((current) => ({
      ...current,
      resultsView: MATCH_RESULT_VIEW_OPTIONS[0].id,
    }));
  }, [profile?.player_id, matchLooCount]);
  const shareProfileUrl = useMemo(() => {
    const id = encodeURIComponent(profile?.player_id || playerId || "");
    if (typeof window === "undefined") return `/u/${id}`;
    const origin = window.location.origin.replace(/\/$/, "");
    return `${origin}/u/${id}`;
  }, [playerId, profile?.player_id]);
  const shareSnapshotText = useMemo(
    () =>
      buildSnapshotText({
        profile,
        grade,
        rankScore,
        minimumRequired,
        lifetimeRanked,
      }),
    [profile, grade, rankScore, minimumRequired, lifetimeRanked]
  );

  const handleCopy = useCallback(async (text, successMessage) => {
    try {
      const copied = await copyTextToClipboard(text);
      if (!copied) throw new Error("Clipboard write failed");
      setShareStatus({ kind: "success", message: successMessage });
    } catch {
      setShareStatus({
        kind: "error",
        message: "Clipboard is unavailable in this browser.",
      });
    }
  }, []);

  useCrackleEffect(rootRef, [
    profile?.player_id,
    grade,
    rankScore,
    hasVisibleScore,
  ]);

  if (loading) {
    return (
      <CompetitionLayout
        generatedAtMs={null}
        stale={false}
        loading={loading}
        onRefresh={refresh}
        faqLinkHref="/"
        faqLinkLabel="View leaderboard"
        vizLinkHref="/learn"
        vizLinkLabel="Interactive explainer"
        top500Href={top500Href}
      >
        <section className="comp-player-empty-card">
          <p>Loading player profile…</p>
        </section>
      </CompetitionLayout>
    );
  }

  if (error) {
    return (
      <CompetitionLayout
        generatedAtMs={null}
        stale={false}
        loading={false}
        onRefresh={refresh}
        faqLinkHref="/"
        faqLinkLabel="View leaderboard"
        vizLinkHref="/learn"
        vizLinkLabel="Interactive explainer"
        top500Href={top500Href}
      >
        <section className="space-y-4">
          <div className="comp-player-error-card">
            <p className="comp-player-error-title">Unable to load player profile</p>
            <p className="comp-player-error-body">{error}</p>
          </div>
          <div className="comp-player-inline-actions">
            <Link to="/" className="comp-player-button">
              Back to leaderboard
            </Link>
            <button
              type="button"
              onClick={refresh}
              className="comp-player-button"
            >
              Retry
            </button>
          </div>
        </section>
      </CompetitionLayout>
    );
  }

  if (!profile) {
    return (
      <CompetitionLayout
        generatedAtMs={null}
        stale={false}
        loading={false}
        onRefresh={refresh}
        faqLinkHref="/"
        faqLinkLabel="View leaderboard"
        vizLinkHref="/learn"
        vizLinkLabel="Interactive explainer"
        top500Href={top500Href}
      >
        <section className="comp-player-empty-card">
          <p>Player not found.</p>
        </section>
      </CompetitionLayout>
    );
  }

  const movementLabel = !profile.delta_has_baseline
    ? "No baseline snapshot yet"
    : profile.delta_is_new
    ? "New entrant since previous snapshot"
    : Number.isFinite(profile.rank_delta) && profile.rank_delta !== 0
    ? `${profile.rank_delta > 0 ? "+" : ""}${profile.rank_delta} rank`
    : "No rank change";

  const remainingToUnlock = Math.max(0, minimumRequired - lifetimeRanked);
  const windowCount = Number(profile.window_tournament_count || 0);
  const windowCoveragePct =
    lifetimeRanked > 0 ? (windowCount / lifetimeRanked) * 100 : null;
  const lastTournamentMs =
    toFiniteNumber(profile.last_tournament_ms) ?? historySummary.latestMs;
  const lastActiveMs =
    toFiniteNumber(profile.last_active_ms) ?? lastTournamentMs;
  const lastSeenLabel = formatRelativeAge(lastTournamentMs, historyReferenceMs);
  const lastActiveLabel = formatRelativeAge(lastActiveMs, historyReferenceMs);
  const snapshotStatusLabel = profile.eligible
    ? "Live on stable leaderboard"
    : hasLifetimeUnlock
    ? "History unlocked, currently off board"
    : `${pluralize(remainingToUnlock, "event")} to unlock`;
  const heroDek = profile.eligible
    ? `${dropStatus.label}. ${pluralize(
        historySummary.recent90Count,
        "ranked tournament"
      )} in the last 90 days.`
    : hasLifetimeUnlock
    ? `This player has enough lifetime history to unlock the profile, but they are not currently in the live stable snapshot.`
    : `Needs ${pluralize(
        remainingToUnlock,
        "more ranked tournament"
      )} before rank and score unlock on the public profile.`;
  const cadenceLabel = historySummary.cadenceDays == null
    ? "No cadence yet"
    : `Every ${formatCompactSpan(historySummary.cadenceDays)}`;
  const rankMotionValue = !profile.delta_has_baseline
    ? "No baseline"
    : profile.delta_is_new
    ? "New entrant"
    : Number.isFinite(profile.rank_delta) && profile.rank_delta !== 0
    ? `${profile.rank_delta > 0 ? "+" : ""}${nf0.format(
        Math.abs(Number(profile.rank_delta)))
      }`
    : "Steady";
  const rankMotionTitle = hasVisibleRank
    ? `Now #${nf0.format(Number(profile.stable_rank))}`
    : hasLifetimeUnlock
    ? "Outside stable leaderboard"
    : "Rank still locked";
  const rankMotionDetail = Number.isFinite(profile.previous_rank)
    ? `Previous snapshot #${nf0.format(Number(profile.previous_rank))}`
    : hasVisibleRank
    ? movementLabel
    : "No prior stable snapshot to compare";
  const scoreSwingValue = !profile.delta_has_baseline
    ? "No baseline"
    : Number.isFinite(profile.display_score_delta)
    ? formatSignedNumber(profile.display_score_delta, nf2)
    : "Steady";
  const scoreSwingTitle = hasVisibleScore
    ? `${nf2.format(rankScore)} current rank score`
    : hasLifetimeUnlock
    ? "Score not published in this snapshot"
    : "Score locked";
  const scoreSwingDetail =
    hasVisibleScore && previousRankScore != null
      ? `Previous snapshot ${nf2.format(previousRankScore)}`
      : hasVisibleScore
      ? scoreHint
      : "Scores appear once the player qualifies for a live stable snapshot";
  const windowPressureDetail = windowCoveragePct == null
    ? "No lifetime tournament data yet"
    : `${nf0.format(windowCoveragePct)}% of lifetime ranked tournaments are still in the active 120d window`;
  const footprintValue =
    tournamentHistory.length > 0
      ? `${pluralize(historySummary.uniqueTeams, "team")} · ${pluralize(
          historySummary.uniqueYears,
          "season year"
        )}`
      : "No archived events";
  const footprintDetail =
    historySummary.firstMs != null && historySummary.latestMs != null
      ? `${formatUtcDate(historySummary.firstMs)} to ${formatUtcDate(
          historySummary.latestMs
        )} · ${formatCompactSpan(historySummary.spanDays)} span`
      : "Tournament archive has not populated yet";
  const recordValue =
    historySummary.knownResults > 0
      ? `${nf0.format(historySummary.wins)}W-${nf0.format(
          historySummary.losses
        )}L`
      : "No logged records";
  const recordDetail =
    historySummary.knownWinRate != null
      ? `${nf0.format(historySummary.knownWinRate)}% win rate across ${pluralize(
          historySummary.knownResults,
          "tracked event"
        )}`
      : "Most archived rows are missing match-level result summaries";
  const activityDetail =
    historySummary.recent365Count > 0
      ? `${pluralize(
          historySummary.recent30Count,
          "event"
        )} in 30d · ${pluralize(historySummary.recent365Count, "event")} in 1y`
      : "No recent tournament timestamps in the archive";
  const visibilityNote =
    profile.ineligible_reason === "insufficient_lifetime_tournaments"
      ? `This player needs ${pluralize(
          remainingToUnlock,
          "more lifetime ranked tournament"
        )} before rank and score unlock.`
      : profile.ineligible_reason === "not_currently_eligible"
      ? "This player has enough lifetime history, but they are currently outside the live stable leaderboard snapshot."
      : null;

  return (
    <CompetitionLayout
      generatedAtMs={profile.generated_at_ms}
      stale={Boolean(profile.stale)}
      loading={loading}
      onRefresh={refresh}
      faqLinkHref="/"
      faqLinkLabel="View leaderboard"
      vizLinkHref="/learn"
      vizLinkLabel="Interactive explainer"
      top500Href={top500Href}
    >
      <section ref={rootRef} className="comp-player-profile">
        <div
          className={`comp-player-hero ${heroHasLightning ? "crackle" : ""}`.trim()}
          data-color={heroHasLightning ? CRACKLE_PURPLE : undefined}
          data-rate={heroHasLightning ? 1.4 : undefined}
        >
          <div className="comp-player-hero-header">
            <div className="comp-player-title-group">
              <p className="comp-player-kicker">Competition profile</p>
              <h2 className="comp-player-name">
                {profile.display_name || "Unknown player"}
              </h2>
              <p className="comp-player-id font-data">{profile.player_id}</p>
              <p className="comp-player-hero-dek">{heroDek}</p>
            </div>
            <div className="comp-player-actions">
              <Link to="/" className="comp-player-button">
                Back to leaderboard
              </Link>
              <button
                type="button"
                onClick={refresh}
                className="comp-player-button"
              >
                Refresh
              </button>
            </div>
          </div>

          <div className="comp-player-hero-band">
            <div className="comp-player-grade-spotlight">
              <p className="comp-player-spotlight-label">Current grade</p>
              <div className="comp-player-grade-row">
                {hasVisibleScore ? (
                  <GradeBadge label={grade} />
                ) : (
                  <span className="comp-player-grade-fallback">
                    {hasLifetimeUnlock ? "Off board" : "Locked"}
                  </span>
                )}
                <span className="comp-player-grade-caption">
                  {snapshotStatusLabel}
                </span>
              </div>

              {hasVisibleScore && (
                <div
                  className={`comp-player-score-track comp-player-score-track--hero is-${scoreTrackTone}`.trim()}
                >
                  <div className="comp-player-score-track-head">
                    <span
                      className="comp-player-track-label"
                      aria-label={`Path to ${trackTarget.label}`}
                    >
                      Path to{" "}
                      <span className="comp-player-track-target">
                        {trackTarget.label}
                      </span>
                    </span>
                    <span className="comp-player-track-value font-data">
                      {nf2.format(rankScore)} / {nf2.format(trackTarget.threshold)}
                    </span>
                  </div>
                  <div className="comp-player-score-rail">
                    <div
                      className={scoreTrackClass}
                      style={{ width: `${scoreProgressPct}%` }}
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="comp-player-hero-stats">
              <HeroStat
                label="Rank"
                value={
                  hasVisibleRank
                    ? `#${nf0.format(Number(profile.stable_rank))}`
                    : "—"
                }
                detail={hasVisibleRank ? movementLabel : snapshotStatusLabel}
                tone="violet"
              />
              <HeroStat
                label="Rank score"
                value={
                  hasVisibleScore ? (
                    <span
                      className={`comp-player-score-value ${
                        scoreHasLightning ? "xxstar-score" : ""
                      }`.trim()}
                    >
                      <span>{nf2.format(rankScore)}</span>
                      <span className="comp-player-score-target">
                        {" "}
                        / {XX_PLUS_THRESHOLD}
                      </span>
                    </span>
                  ) : (
                    "—"
                  )
                }
                detail={hasVisibleScore ? scoreHint : "Score hidden in this snapshot"}
                tone={scoreHasLightning ? "amber" : "cyan"}
              />
              <HeroStat
                label="Window"
                value={`${nf0.format(windowCount)} / ${nf0.format(
                  minimumRequired
                )}`}
                detail={dropStatus.label}
                tone="emerald"
              />
              <HeroStat
                label="Last seen"
                value={lastSeenLabel}
                detail={formatUtcDateTime(lastTournamentMs)}
                tone="rose"
              />
            </div>
          </div>

          <div className="comp-player-fact-row">
            <FactChip
              label="Snapshot"
              value={profile.eligible ? "Live" : "Off board"}
              tone={profile.eligible ? "emerald" : "amber"}
            />
            <FactChip
              label="Lifetime ranked"
              value={nf0.format(lifetimeRanked)}
              tone="violet"
            />
            <FactChip
              label="90d activity"
              value={pluralize(historySummary.recent90Count, "event")}
              tone="cyan"
            />
            <FactChip
              label="Primary team"
              value={historySummary.primaryTeam?.label || "Unknown"}
              tone="rose"
            />
            <FactChip
              label="Archive span"
              value={
                historySummary.spanDays != null
                  ? formatCompactSpan(historySummary.spanDays)
                  : "—"
              }
              tone="slate"
            />
          </div>
        </div>

        {!profile.eligible && visibilityNote && (
          <div className="comp-player-note comp-player-note--warn">
            <p className="comp-player-note-title">Player is not currently eligible</p>
            <p className="comp-player-note-body">{visibilityNote}</p>
          </div>
        )}

        {!hasLifetimeUnlock && (
          <div className="comp-player-note">
            <p className="comp-player-note-body">
              Progress to eligibility:{" "}
              <span className="comp-player-note-strong">
                {nf0.format(Number(progress.current || 0))}/
                {nf0.format(Number(progress.required || minimumRequired))}
              </span>{" "}
              ranked tournaments
            </p>
            <div className="comp-player-eligibility-rail">
              <div
                className="comp-player-eligibility-fill"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>
        )}

        <div className="comp-player-dossier-grid">
          <section className="comp-player-panel comp-player-overview-panel">
            <div className="comp-player-panel-head">
              <div>
                <h3 className="comp-player-panel-title">Snapshot briefing</h3>
                <p className="comp-player-panel-subtitle">
                  Derived from the live snapshot plus the cached tournament archive.
                </p>
              </div>
              <p className="comp-player-panel-meta">
                Updated {formatUtcDateTime(historyGeneratedAtMs)}
              </p>
            </div>

            <div className="comp-player-summary-grid">
              <SummaryCard
                value={rankMotionValue}
                title={rankMotionTitle}
                detail={rankMotionDetail}
                tone="violet"
              />
              <SummaryCard
                value={scoreSwingValue}
                title={scoreSwingTitle}
                detail={scoreSwingDetail}
                tone="cyan"
              />
              <SummaryCard
                value={dropStatus.label}
                title={`${nf0.format(windowCount)} active-window tournaments`}
                detail={windowPressureDetail}
                tone="amber"
              />
              <SummaryCard
                value={cadenceLabel}
                title={lastActiveLabel === "—" ? "No recent timestamp" : `Last active ${lastActiveLabel}`}
                detail={activityDetail}
                tone="emerald"
              />
              <SummaryCard
                value={footprintValue}
                title={
                  historySummary.busiestYear
                    ? `Busiest year ${historySummary.busiestYear.label}`
                    : "Archive still sparse"
                }
                detail={footprintDetail}
                tone="rose"
              />
              <SummaryCard
                value={recordValue}
                title={
                  historySummary.positive > 0
                    ? `${pluralize(historySummary.positive, "positive finish")}`
                    : "No positive-result rows yet"
                }
                detail={recordDetail}
                tone="slate"
              />
            </div>

            {historySummary.recentEvents.length > 0 && (
              <div className="comp-player-recent-section">
                <div className="comp-player-panel-head comp-player-panel-head--tight">
                  <div>
                    <h4 className="comp-player-panel-title">Recent stretch</h4>
                    <p className="comp-player-panel-subtitle">
                      The latest archived tournaments on this profile.
                    </p>
                  </div>
                </div>
                <div className="comp-player-recent-grid">
                  {historySummary.recentEvents.map((row) => (
                    <RecentEventCard
                      key={row.key}
                      row={row}
                      referenceMs={historyReferenceMs}
                    />
                  ))}
                </div>
              </div>
            )}
          </section>

          <aside className="comp-player-side-rail">
            <section className="comp-player-panel">
              <div className="comp-player-panel-head">
                <h3 className="comp-player-panel-title">Competition pulse</h3>
                <p className="comp-player-panel-meta">
                  {nf0.format(historyCount)} cached rows
                </p>
              </div>
              <div className="comp-player-pulse-list">
                <PulseRow
                  label="Last tournament"
                  value={lastSeenLabel}
                  detail={formatUtcDateTime(lastTournamentMs)}
                />
                <PulseRow
                  label="Last active"
                  value={lastActiveLabel}
                  detail={formatUtcDateTime(lastActiveMs)}
                />
                <PulseRow
                  label="Window coverage"
                  value={
                    windowCoveragePct == null
                      ? "—"
                      : `${nf0.format(windowCoveragePct)}%`
                  }
                  detail={`${nf0.format(windowCount)} of ${nf0.format(
                    lifetimeRanked
                  )} lifetime tournaments are in the active window`}
                />
                <PulseRow
                  label="Most common team"
                  value={historySummary.primaryTeam?.label || "Unknown"}
                  detail={
                    historySummary.primaryTeam
                      ? `${pluralize(
                          historySummary.primaryTeam.count,
                          "appearance"
                        )} in archive`
                      : "No tagged team names in archive yet"
                  }
                />
                <PulseRow
                  label="Archive coverage"
                  value={
                    historySummary.knownCoveragePct == null
                      ? "—"
                      : `${nf0.format(historySummary.knownCoveragePct)}%`
                  }
                  detail={`${pluralize(
                    historySummary.knownResults,
                    "row"
                  )} include a match record`}
                />
              </div>

              {historySummary.recentForm.length > 0 && (
                <>
                  <div className="comp-player-panel-head comp-player-panel-head--tight">
                    <h4 className="comp-player-panel-title">Recent form</h4>
                    <p className="comp-player-panel-meta">
                      Last {nf0.format(historySummary.recentForm.length)}
                    </p>
                  </div>
                  <div className="comp-player-form-strip">
                    {historySummary.recentForm.map((entry) => (
                      <FormPill key={entry.key} entry={entry} />
                    ))}
                  </div>
                </>
              )}
            </section>

            <section className="comp-player-panel comp-player-share-panel">
              <h3 className="comp-player-panel-title">Share profile</h3>
              <p className="comp-player-panel-subtitle">
                Copy a direct link or snapshot text for Discord, socials, and team chats.
              </p>
              <div className="comp-player-share-actions">
                <button
                  type="button"
                  onClick={() => handleCopy(shareProfileUrl, "Profile link copied.")}
                  className="comp-player-button comp-player-button--small"
                >
                  Copy profile link
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleCopy(shareSnapshotText, "Profile snapshot text copied.")
                  }
                  className="comp-player-button comp-player-button--small"
                >
                  Copy profile snapshot
                </button>
              </div>
              <p className="comp-player-link-preview">{shareProfileUrl}</p>
              {shareStatus && (
                <p
                  className={`comp-player-share-status ${
                    shareStatus.kind === "error"
                      ? "comp-player-share-status--error"
                      : "comp-player-share-status--ok"
                  }`}
                >
                  {shareStatus.message}
                </p>
              )}
            </section>

            {(historySummary.knownResults === 0 ||
              historySummary.placementNotes < tournamentHistory.length) && (
              <p className="comp-player-note-tip">
                Some archived tournaments are missing team names, match records, or
                placement notes, so the profile emphasizes the data that is actually
                present instead of guessing.
              </p>
            )}
          </aside>
        </div>

        <div className="comp-player-main-grid">
          {hasMatchImpactPanel && (
            <section className="comp-player-panel comp-player-impact-panel">
              <div className="comp-player-panel-head">
                <div>
                  <div className="comp-player-panel-title-row">
                    <h3 className="comp-player-panel-title">
                      Strongest results
                    </h3>
                    <button
                      type="button"
                      className="comp-player-help-dot"
                      title={MATCH_RESULTS_TECHNICAL_NOTE}
                      aria-label={MATCH_RESULTS_TECHNICAL_NOTE}
                    >
                      ?
                    </button>
                  </div>
                </div>
              </div>

              {matchLooImpacts.length > 0 ? (
                <>
                  <div className="comp-player-impact-toolbar">
                    <div
                      className="comp-player-impact-view-toggle"
                      role="toolbar"
                      aria-label="Strongest results views"
                    >
                      {MATCH_RESULT_VIEW_OPTIONS.map((option) => {
                        const isActive = activeMatchImpactView.id === option.id;
                        return (
                          <button
                            key={option.id}
                            type="button"
                            aria-pressed={isActive}
                            className={`comp-player-impact-view-button is-${option.tone}${
                              isActive ? " is-active" : ""
                            }`.trim()}
                            onClick={() =>
                              setPageState((current) => ({
                                ...current,
                                resultsView: option.id,
                              }))
                            }
                          >
                            {option.label}
                          </button>
                        );
                      })}
                    </div>
                    <div className="comp-player-impact-stat-row">
                      <p className="comp-player-impact-stat">
                        Best{" "}
                        <span className="font-data">
                          {strongestHelpfulImpact
                            ? formatSignedNumber(
                                strongestHelpfulImpact.contributionDelta,
                                nf2,
                                nf2.format(0)
                              )
                            : "—"}
                        </span>
                      </p>
                      <p className="comp-player-impact-stat">
                        Worst{" "}
                        <span className="font-data">
                          {strongestHarmfulImpact
                            ? formatSignedNumber(
                                strongestHarmfulImpact.contributionDelta,
                                nf2,
                                nf2.format(0)
                              )
                            : "—"}
                        </span>
                      </p>
                      <p className="comp-player-impact-stat">
                        {nf0.format(matchLooCount)} shortlisted
                      </p>
                    </div>
                  </div>

                  <MatchImpactTable
                    rows={activeMatchImpactRows}
                    emptyText={activeMatchImpactView.emptyText}
                    referenceMs={historyReferenceMs}
                    highlightedPlayerNames={matchImpactHighlightedPlayerNames}
                    showDirection={activeMatchImpactView.id === "swings"}
                  />
                </>
              ) : (
                <p className="comp-player-empty-text">
                  This snapshot does not include shortlisted match-impact rows yet.
                </p>
              )}
            </section>
          )}

          <section className="comp-player-panel comp-player-history-panel">
            <div className="comp-player-panel-head">
              <div>
                <h3 className="comp-player-panel-title">Ranked history explorer</h3>
                <p className="comp-player-panel-subtitle">
                  Filter the cached ranked tournament archive by time, outcome, or team.
                </p>
              </div>
              <p className="comp-player-panel-meta">
                {nf0.format(filteredHistory.length)} matching
              </p>
            </div>

            <div className="comp-player-insight-row">
              <InsightChip
                label="Total tournaments"
                value={nf0.format(tournamentHistory.length)}
                tone="violet"
              />
              <InsightChip
                label="Known match record"
                value={`${nf0.format(historySummary.wins)}W-${nf0.format(
                  historySummary.losses
                )}L`}
                tone="emerald"
              />
              <InsightChip
                label="Positive events"
                value={nf0.format(historySummary.positive)}
                tone="amber"
              />
              <InsightChip
                label="Teams played"
                value={nf0.format(historySummary.uniqueTeams)}
                tone="rose"
              />
              <InsightChip
                label="90d activity"
                value={nf0.format(historySummary.recent90Count)}
                tone="cyan"
              />
              <InsightChip
                label="Avg matches"
                value={
                  historySummary.averageMatches == null
                    ? "—"
                    : nf2.format(historySummary.averageMatches)
                }
                tone="slate"
              />
            </div>

            <div className="comp-player-controls-strip">
              <input
                type="search"
                value={historyQuery}
                onChange={(event) => {
                  setHistoryQuery(event.target.value);
                  setPageState((current) => ({ ...current, history: 1 }));
                }}
                placeholder="Search tournaments or teams"
                className="comp-player-control"
              />
              <select
                value={historyYear}
                onChange={(event) => {
                  setHistoryYear(event.target.value);
                  setPageState((current) => ({ ...current, history: 1 }));
                }}
                className="comp-player-control"
              >
                <option value="all">All years</option>
                {historyYears.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
              <select
                value={historyOutcome}
                onChange={(event) => {
                  setHistoryOutcome(event.target.value);
                  setPageState((current) => ({ ...current, history: 1 }));
                }}
                className="comp-player-control"
              >
                <option value="all">All outcomes</option>
                <option value="positive">Positive results</option>
                <option value="even">Even results</option>
                <option value="negative">Negative results</option>
                <option value="unknown">Unknown results</option>
              </select>
              <select
                value={historySort}
                onChange={(event) => {
                  setHistorySort(event.target.value);
                  setPageState((current) => ({ ...current, history: 1 }));
                }}
                className="comp-player-control"
              >
                <option value="recent">Newest first</option>
                <option value="oldest">Oldest first</option>
                <option value="most_matches">Most matches</option>
              </select>
            </div>

            {historyRows.length ? (
              <>
                <div className="comp-player-table-wrap">
                  <div className="comp-player-table-scroll">
                    <table className="comp-player-table">
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Tournament</th>
                          <th>Team</th>
                          <th>Result</th>
                        </tr>
                      </thead>
                      <tbody>
                        {historyRows.map((row) => (
                          <tr key={row.key}>
                            <td className="font-data comp-player-table-date">
                              {formatUtcDateTime(row.eventMs)}
                            </td>
                            <td>
                              <p className="comp-player-table-primary">
                                {row.tournamentName}
                              </p>
                              {row.tournamentId && (
                                <p className="comp-player-table-secondary">
                                  Tournament {row.tournamentId}
                                </p>
                              )}
                            </td>
                            <td>
                              <p className="comp-player-table-primary">
                                {row.teamName || "Unknown team"}
                              </p>
                              {row.teamId && (
                                <p className="comp-player-table-secondary">
                                  Team {row.teamId}
                                </p>
                              )}
                            </td>
                            <td>
                              <p className="font-data comp-player-table-primary">
                                {row.resultSummary || row.placementLabel || "—"}
                              </p>
                              {row.matchesPlayed != null && (
                                <p className="comp-player-table-secondary">
                                  {nf0.format(row.matchesPlayed)} matches
                                </p>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
                <div className="comp-player-pagination">
                  <p className="comp-player-panel-subtitle">
                    Showing page {nf0.format(safeHistoryPage)} of{" "}
                    {nf0.format(historyPageCount)}
                  </p>
                  <div className="comp-player-inline-actions">
                    <button
                      type="button"
                      onClick={() =>
                        setPageState((current) => ({
                          ...current,
                          history: Math.max(1, current.history - 1),
                        }))
                      }
                      disabled={safeHistoryPage <= 1}
                      className="comp-player-button comp-player-button--small"
                    >
                      Prev
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        setPageState((current) => ({
                          ...current,
                          history: Math.min(
                            historyPageCount,
                            current.history + 1
                          ),
                        }))
                      }
                      disabled={safeHistoryPage >= historyPageCount}
                      className="comp-player-button comp-player-button--small"
                    >
                      Next
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <p className="comp-player-empty-text">
                No history rows match these filters yet.
              </p>
            )}
          </section>
        </div>
      </section>
    </CompetitionLayout>
  );
};

export default CompetitionPlayerPage;
