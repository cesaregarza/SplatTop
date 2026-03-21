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
const MATCH_LOO_DISPLAY_SCALE = 25;
const MINUTE_MS = 60 * 1000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;
const MATCH_RESULTS_TECHNICAL_NOTE =
  "Technical note: leave-one-out shortlist from this ranking run. Contribution is the negated score delta after removing one shortlisted match.";
const EMPTY_TEXT_LIST = Object.freeze([]);
const EMPTY_EXPANDED_ROWS = Object.freeze({});
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

const HeaderMetric = ({
  label,
  value,
  detail,
  tone = "slate",
  title,
  wide = false,
  progressPct = null,
  progressClassName = "",
  progressLabel,
}) => (
  <div
    className={`comp-player-header-stat is-${tone}${
      wide ? " is-wide" : ""
    }`.trim()}
    title={title}
  >
    <span className="comp-player-header-stat-label">{label}</span>
    <span className="comp-player-header-stat-value">{value}</span>
    {detail ? <span className="comp-player-header-stat-detail">{detail}</span> : null}
    {progressPct != null ? (
      <div
        className="comp-player-header-progress"
        aria-label={progressLabel}
      >
        <div
          className={`comp-player-header-progress-fill ${progressClassName}`.trim()}
          style={{ width: `${progressPct}%` }}
        />
      </div>
    ) : null}
  </div>
);

const AtGlanceItem = ({ label, value }) => (
  <div className="comp-player-glance-item">
    <dt className="comp-player-glance-label">{label}</dt>
    <dd className="comp-player-glance-value">
      <span className="font-data">{value}</span>
    </dd>
  </div>
);

const RecentEventRow = ({ row, referenceMs }) => {
  const outcomeLabel =
    row.outcome === "positive"
      ? "W"
      : row.outcome === "negative"
      ? "L"
      : row.outcome === "even"
      ? "="
      : "?";
  const resultLabel =
    row.resultSummary || row.placementLabel || "Result not logged";
  const hasTournamentLink = Boolean(row.tournamentId);

  return (
    <tr
      key={row.key}
      className={hasTournamentLink ? "comp-player-table-row is-clickable" : "comp-player-table-row"}
      role={hasTournamentLink ? "link" : undefined}
      tabIndex={hasTournamentLink ? 0 : undefined}
      onClick={
        hasTournamentLink
          ? () => openTournamentUrl(row.tournamentId)
          : undefined
      }
      onKeyDown={
        hasTournamentLink
          ? (event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openTournamentUrl(row.tournamentId);
              }
            }
          : undefined
      }
    >
      <td
        className="font-data comp-player-table-date"
        title={formatUtcDateTime(row.eventMs)}
      >
        {formatRelativeAge(row.eventMs, referenceMs)}
      </td>
      <td>
        <p className="comp-player-table-primary">{row.tournamentName}</p>
      </td>
      <td>
        <p className="comp-player-table-primary">{row.teamName || "Unknown team"}</p>
      </td>
      <td>
        <div className="comp-player-result-inline">
          <span className={`comp-player-result-pill is-${row.outcome}`.trim()}>
            {outcomeLabel}
          </span>
          <p className="font-data comp-player-table-primary">{resultLabel}</p>
        </div>
      </td>
    </tr>
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

const openMatchUrl = (matchUrl) => {
  if (!matchUrl || typeof window === "undefined") return;
  window.open(matchUrl, "_blank", "noopener,noreferrer");
};

const openTournamentUrl = (tournamentId) => {
  if (!tournamentId || typeof window === "undefined") return;
  window.open(
    `https://sendou.ink/to/${encodeURIComponent(tournamentId)}`,
    "_blank",
    "noopener,noreferrer"
  );
};

const MatchImpactRow = ({
  row,
  referenceMs,
  highlightedPlayerNames = EMPTY_TEXT_LIST,
  expanded = false,
  onToggleExpand,
}) => {
  const tone = toneForMatchImpact(row);
  const hasLineups =
    row.playerTeamPlayers.length > 0 || row.opponentTeamPlayers.length > 0;
  const contribution = formatSignedNumber(
    row.contributionDelta,
    nf2,
    nf2.format(0)
  );
  const eventLabel =
    row.eventMs == null
      ? "Date unavailable"
      : formatRelativeAge(row.eventMs, referenceMs);
  const playerTeamLabel = row.playerTeamName || "Unknown team";
  const opponentTeamLabel = row.opponentTeamName || "Unknown opponent";
  const matchupLabel =
    row.playerTeamName || row.opponentTeamName
      ? `${playerTeamLabel} vs ${opponentTeamLabel}`
      : "Teams unavailable";
  const finalScoreLabel =
    row.playerTeamScore != null && row.opponentTeamScore != null
      ? `${nf0.format(row.playerTeamScore)}-${nf0.format(
          row.opponentTeamScore
        )}`
      : "Score unavailable";
  const winMark =
    row.isWin == null ? "?" : row.isWin ? "W" : "L";
  const rowBody = (
    <div className="comp-player-impact-row-shell">
      <div className="comp-player-impact-row-primary">
        <div className="comp-player-impact-row-event">
          <p className="comp-player-impact-row-title">
            <span
              className="comp-player-impact-row-title-text"
              title={row.tournamentName}
            >
              {row.tournamentName}
            </span>
            <span
              className="comp-player-impact-row-meta"
              title={formatUtcDateTime(row.eventMs)}
            >
              {eventLabel}
            </span>
          </p>
        </div>
        <div className="comp-player-impact-row-result">
          <p className="comp-player-impact-row-matchup-text">
            <span>{matchupLabel}</span>
            <span
              className={`comp-player-impact-score-dot is-${row.outcome}`.trim()}
              aria-hidden="true"
            />
            <span className="comp-player-impact-row-score">
              {finalScoreLabel}
            </span>
            <span className="comp-player-impact-row-score-state">{winMark}</span>
          </p>
        </div>
        <div className="comp-player-impact-row-summary">
          <p className="comp-player-impact-row-delta font-data">{contribution}</p>
          {hasLineups ? (
            <button
              type="button"
              className="comp-player-impact-toggle"
              aria-label={expanded ? "Hide lineups" : "Show lineups"}
              onClick={(event) => {
                event.stopPropagation();
                onToggleExpand?.();
              }}
            >
              {expanded ? "▾" : "▸"}
            </button>
          ) : null}
        </div>
      </div>
      {expanded && hasLineups ? (
        <div className="comp-player-impact-expanded">
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
      ) : null}
    </div>
  );

  return (
    <article
      className={`comp-player-impact-row is-${tone} ${
        row.matchUrl ? "is-clickable" : ""
      }`.trim()}
      role={row.matchUrl ? "link" : undefined}
      tabIndex={row.matchUrl ? 0 : undefined}
      onClick={row.matchUrl ? () => openMatchUrl(row.matchUrl) : undefined}
      onKeyDown={
        row.matchUrl
          ? (event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openMatchUrl(row.matchUrl);
              }
            }
          : undefined
      }
    >
      {rowBody}
    </article>
  );
};

const MatchImpactTable = ({
  rows,
  emptyText,
  referenceMs,
  highlightedPlayerNames,
  expandedRows = EMPTY_EXPANDED_ROWS,
  onToggleExpand,
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
              expanded={Boolean(expandedRows[row.key])}
              onToggleExpand={() => onToggleExpand?.(row.key)}
            />
          ))}
        </div>
      </div>
    ) : (
      <p className="comp-player-empty-text">{emptyText}</p>
    )
  );
};

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
    dataTab: "history",
    expandedImpactRows: {},
  });
  const [shareStatus, setShareStatus] = useState(null);
  const [shareMenuOpen, setShareMenuOpen] = useState(false);
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
  const scoreHasLightning =
    rankScore != null && (rankScore >= XX_PLUS_THRESHOLD || grade === "XX★");
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
  const hasMatchImpactPanel = matchLooCount > 0 || matchLooImpacts.length > 0;
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
  const strongestHarmfulImpact = harmfulMatchImpacts[0] || null;
  const strongestHelpfulImpact = helpfulMatchImpacts[0] || null;
  const activeMatchImpactView =
    MATCH_RESULT_VIEW_OPTIONS.find(
      (option) => option.id === pageState.resultsView
    ) || MATCH_RESULT_VIEW_OPTIONS[0];
  const activeDataTab =
    pageState.dataTab || (hasMatchImpactPanel ? "results" : "history");
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
      dataTab: hasMatchImpactPanel ? "results" : "history",
      expandedImpactRows: {},
    }));
  }, [profile?.player_id, matchLooCount, hasMatchImpactPanel]);
  useEffect(() => {
    setShareMenuOpen(false);
    setShareStatus(null);
  }, [profile?.player_id]);
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
    setShareMenuOpen(false);
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
  const toggleImpactExpansion = useCallback((rowKey) => {
    setPageState((current) => ({
      ...current,
      expandedImpactRows: {
        ...current.expandedImpactRows,
        [rowKey]: !current.expandedImpactRows[rowKey],
      },
    }));
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
    ? "No previous update yet"
    : profile.delta_is_new
    ? "New entrant since previous update"
    : Number.isFinite(profile.rank_delta) && profile.rank_delta !== 0
    ? `${profile.rank_delta > 0 ? "+" : ""}${profile.rank_delta} rank`
    : "No rank change";

  const remainingToUnlock = Math.max(0, minimumRequired - lifetimeRanked);
  const windowCount = Number(profile.window_tournament_count || 0);
  const lastTournamentMs =
    toFiniteNumber(profile.last_tournament_ms) ?? historySummary.latestMs;
  const lastActiveMs =
    toFiniteNumber(profile.last_active_ms) ?? lastTournamentMs;
  const lastSeenLabel = formatRelativeAge(lastTournamentMs, historyReferenceMs);
  const lastActiveLabel = formatRelativeAge(lastActiveMs, historyReferenceMs);
  const recordValue =
    historySummary.knownResults > 0
      ? `${nf0.format(historySummary.wins)}W-${nf0.format(
          historySummary.losses
        )}L`
      : "No logged records";
  const snapshotStatusLabel = profile.eligible
    ? "Live on stable leaderboard"
    : hasLifetimeUnlock
    ? "History unlocked, currently off board"
    : `${pluralize(remainingToUnlock, "event")} to unlock`;
  const winRateValue =
    historySummary.knownWinRate != null
      ? `${nf0.format(historySummary.knownWinRate)}%`
      : "—";
  const averageMatchesValue =
    historySummary.averageMatches == null
      ? "—"
      : nf2.format(historySummary.averageMatches);
  const recentActivityValue =
    historySummary.recent365Count > 0
      ? `${nf0.format(historySummary.recent30Count)} in 30d · ${nf0.format(
          historySummary.recent365Count
        )} in 1y`
      : "No recent archive activity";
  const historySummaryLine = `${nf0.format(
    tournamentHistory.length
  )} tournaments · ${recordValue} · ${nf0.format(
    historySummary.positive
  )} positive · ${nf0.format(historySummary.uniqueTeams)} teams · ${averageMatchesValue} avg matches`;
  const headerScoreDetail =
    rankScore == null
      ? "Score hidden"
      : scoreDeltaToThreshold >= 0
      ? `${nf2.format(scoreDeltaToThreshold)} above ${trackTarget.label}`
      : `${nf2.format(Math.abs(scoreDeltaToThreshold))} to ${trackTarget.label}`;
  const headerRankLabel = hasVisibleRank
    ? `#${nf0.format(Number(profile.stable_rank))}`
    : hasLifetimeUnlock
    ? "Off board"
    : "Locked";
  const resultsHeaderSummary = `Best ${
    strongestHelpfulImpact
      ? formatSignedNumber(
          strongestHelpfulImpact.contributionDelta,
          nf2,
          nf2.format(0)
        )
      : "—"
  } · Worst ${
    strongestHarmfulImpact
      ? formatSignedNumber(
          strongestHarmfulImpact.contributionDelta,
          nf2,
          nf2.format(0)
        )
      : "—"
  } · ${nf0.format(matchLooCount)} shortlisted`;
  const resultsUpdatedMs =
    toFiniteNumber(profile?.match_loo_generated_at_ms) ??
    toFiniteNumber(profile?.generated_at_ms);
  const resultsUpdatedLabel =
    resultsUpdatedMs == null
      ? null
      : `Results updated ${formatRelativeAge(resultsUpdatedMs)}`;
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
              <div className="comp-player-title-row">
                <h2 className="comp-player-name">
                  {profile.display_name || "Unknown player"}
                </h2>
                <span className="comp-player-title-id font-data">
                  {profile.player_id}
                </span>
                {hasVisibleScore ? (
                  <GradeBadge label={grade} />
                ) : (
                  <span className="comp-player-grade-fallback">
                    {hasLifetimeUnlock ? "Off board" : "Locked"}
                  </span>
                )}
                <span className="comp-player-rank-chip font-data">
                  {headerRankLabel}
                </span>
                {hasVisibleRank && movementLabel !== "No rank change" ? (
                  <span className="comp-player-rank-trend">{movementLabel}</span>
                ) : null}
              </div>
            </div>
            <div className="comp-player-hero-controls">
              <div className="comp-player-actions">
                <Link to="/" className="comp-player-back-link">
                  Back
                </Link>
                <div className="comp-player-share-menu">
                  <button
                    type="button"
                    aria-expanded={shareMenuOpen}
                    onClick={() => setShareMenuOpen((current) => !current)}
                    className="comp-player-button comp-player-button--small"
                  >
                    Share
                  </button>
                  {shareMenuOpen ? (
                    <div className="comp-player-share-popover">
                      <button
                        type="button"
                        className="comp-player-share-action"
                        onClick={() =>
                          handleCopy(shareProfileUrl, "Profile link copied.")
                        }
                      >
                        Copy link
                      </button>
                      <button
                        type="button"
                        className="comp-player-share-action"
                        onClick={() =>
                          handleCopy(
                            shareSnapshotText,
                            "Profile snapshot text copied."
                          )
                        }
                      >
                        Copy snapshot
                      </button>
                    </div>
                  ) : null}
                </div>
              </div>
              {shareStatus ? (
                <p
                  className={`comp-player-share-status ${
                    shareStatus.kind === "error"
                      ? "comp-player-share-status--error"
                      : "comp-player-share-status--ok"
                  }`}
                >
                  {shareStatus.message}
                </p>
              ) : null}
            </div>
          </div>

          <div className="comp-player-hero-summary">
            <div className="comp-player-header-metrics">
              <HeaderMetric
                label="Score"
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
                        / {nf0.format(trackTarget.threshold)}
                      </span>
                    </span>
                  ) : (
                    "—"
                  )
                }
                detail={headerScoreDetail}
                tone={scoreHasLightning ? "amber" : "cyan"}
                wide
                progressPct={hasVisibleScore ? scoreProgressPct : null}
                progressLabel={`Path to ${trackTarget.label}`}
                progressClassName={
                  rankScore != null && rankScore >= XX_PLUS_THRESHOLD
                    ? "is-threshold"
                    : ""
                }
              />
              <HeaderMetric
                label="Active"
                value={`${nf0.format(windowCount)}/${nf0.format(
                  minimumRequired
                )}`}
                detail={dropStatus.label}
                tone="emerald"
              />
              <HeaderMetric
                label="Record"
                value={recordValue}
                detail={
                  historySummary.positive > 0
                    ? `${pluralize(historySummary.positive, "positive finish")}`
                    : snapshotStatusLabel
                }
                tone="violet"
              />
              <HeaderMetric
                label="Last active"
                value={lastActiveLabel}
                detail={lastTournamentMs == null ? "No recent timestamp" : `Last tournament ${lastSeenLabel}`}
                tone="rose"
                title={formatUtcDateTime(lastActiveMs)}
              />
            </div>
            <dl className="comp-player-hero-glance">
              <AtGlanceItem label="Win rate" value={winRateValue} />
              <AtGlanceItem label="Recent activity" value={recentActivityValue} />
              <AtGlanceItem
                label="Teams"
                value={nf0.format(historySummary.uniqueTeams)}
              />
              <AtGlanceItem label="Avg matches" value={averageMatchesValue} />
              <AtGlanceItem
                label="Lifetime ranked"
                value={nf0.format(lifetimeRanked)}
              />
            </dl>
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

        {historySummary.recentEvents.length > 0 ? (
          <section className="comp-player-panel comp-player-recent-panel">
            <div className="comp-player-panel-head">
              <h3 className="comp-player-panel-title">Recent activity</h3>
              <p className="comp-player-panel-meta">
                Last {nf0.format(historySummary.recentEvents.length)}
              </p>
            </div>
            <div className="comp-player-table-wrap">
              <div className="comp-player-table-scroll">
                <table className="comp-player-table comp-player-table--compact">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Tournament</th>
                      <th>Team</th>
                      <th>Result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {historySummary.recentEvents.map((row) => (
                      <RecentEventRow
                        key={row.key}
                        row={row}
                        referenceMs={historyReferenceMs}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        ) : null}

        <section className="comp-player-panel comp-player-data-panel">
          <div className="comp-player-panel-head comp-player-data-head">
            <div
              className="comp-player-data-tabs"
              role="tablist"
              aria-label="Profile data views"
            >
              {hasMatchImpactPanel ? (
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeDataTab === "results"}
                  className={`comp-player-data-tab${
                    activeDataTab === "results" ? " is-active" : ""
                  }`.trim()}
                  onClick={() =>
                    setPageState((current) => ({
                      ...current,
                      dataTab: "results",
                    }))
                  }
                >
                  Strongest results
                </button>
              ) : null}
              <button
                type="button"
                role="tab"
                aria-selected={activeDataTab === "history"}
                className={`comp-player-data-tab${
                  activeDataTab === "history" ? " is-active" : ""
                }`.trim()}
                onClick={() =>
                  setPageState((current) => ({
                    ...current,
                    dataTab: "history",
                  }))
                }
              >
                History explorer
              </button>
            </div>
            <div className="comp-player-data-meta">
              <p className="comp-player-impact-toolbar-summary">
                {activeDataTab === "results"
                  ? resultsHeaderSummary
                  : `${historySummaryLine} · ${nf0.format(
                      filteredHistory.length
                    )} matching`}
              </p>
              {activeDataTab === "results" && resultsUpdatedLabel ? (
                <p
                  className="comp-player-panel-subtitle"
                  title={formatUtcDateTime(resultsUpdatedMs)}
                >
                  {resultsUpdatedLabel}
                </p>
              ) : null}
              {activeDataTab === "results" ? (
                <button
                  type="button"
                  className="comp-player-help-dot"
                  title={MATCH_RESULTS_TECHNICAL_NOTE}
                  aria-label={MATCH_RESULTS_TECHNICAL_NOTE}
                >
                  ?
                </button>
              ) : null}
            </div>
          </div>

          {activeDataTab === "results" && hasMatchImpactPanel ? (
            <div className="comp-player-data-section comp-player-data-section--results">
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
                                expandedImpactRows: {},
                              }))
                            }
                          >
                            {option.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="comp-player-data-body">
                    <MatchImpactTable
                      rows={activeMatchImpactRows}
                      emptyText={activeMatchImpactView.emptyText}
                      referenceMs={historyReferenceMs}
                      highlightedPlayerNames={matchImpactHighlightedPlayerNames}
                      expandedRows={pageState.expandedImpactRows}
                      onToggleExpand={toggleImpactExpansion}
                    />
                  </div>
                </>
              ) : (
                <div className="comp-player-data-body">
                  <p className="comp-player-empty-text">
                    This snapshot does not include shortlisted match-impact rows yet.
                  </p>
                </div>
              )}
            </div>
          ) : null}

          {activeDataTab === "history" ? (
            <div className="comp-player-data-section comp-player-data-section--history">
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
                  <div className="comp-player-data-body">
                    <div className="comp-player-table-wrap">
                      <div className="comp-player-table-scroll">
                        <table className="comp-player-table comp-player-table--compact">
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
                              <tr
                                key={row.key}
                                className={
                                  row.tournamentId
                                    ? "comp-player-table-row is-clickable"
                                    : "comp-player-table-row"
                                }
                                role={row.tournamentId ? "link" : undefined}
                                tabIndex={row.tournamentId ? 0 : undefined}
                                onClick={
                                  row.tournamentId
                                    ? () => openTournamentUrl(row.tournamentId)
                                    : undefined
                                }
                                onKeyDown={
                                  row.tournamentId
                                    ? (event) => {
                                        if (
                                          event.key === "Enter" ||
                                          event.key === " "
                                        ) {
                                          event.preventDefault();
                                          openTournamentUrl(row.tournamentId);
                                        }
                                      }
                                    : undefined
                                }
                              >
                                <td
                                  className="font-data comp-player-table-date"
                                  title={formatUtcDateTime(row.eventMs)}
                                >
                                  {formatRelativeAge(row.eventMs, historyReferenceMs)}
                                </td>
                                <td>
                                  <p className="comp-player-table-primary">
                                    {row.tournamentName}
                                  </p>
                                </td>
                                <td>
                                  <p className="comp-player-table-primary">
                                    {row.teamName || "Unknown team"}
                                  </p>
                                </td>
                                <td>
                                  <p className="font-data comp-player-table-primary">
                                    {row.resultSummary || row.placementLabel || "—"}
                                    {row.matchesPlayed != null
                                      ? ` · ${nf0.format(row.matchesPlayed)} matches`
                                      : ""}
                                  </p>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                  <div className="comp-player-data-footer comp-player-pagination">
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
                <div className="comp-player-data-body">
                  <p className="comp-player-empty-text">
                    No history rows match these filters yet.
                  </p>
                </div>
              )}
            </div>
          ) : null}
        </section>

        {(historySummary.knownResults === 0 ||
          historySummary.placementNotes < tournamentHistory.length) && (
          <p className="comp-player-note-tip">
            Some archived tournaments are missing team names, match records, or
            placement notes, so the profile emphasizes the data that is actually
            present instead of guessing.
          </p>
        )}
      </section>
    </CompetitionLayout>
  );
};

export default CompetitionPlayerPage;
