import React from "react";
import { Link } from "react-router-dom";
import {
  CRACKLE_PURPLE,
  nf0,
  nf2,
  tierFor,
} from "./stableLeaderboardUtils";
import {
  EMPTY_EXPANDED_ROWS,
  EMPTY_TEXT_LIST,
  formatRelativeAge,
  formatSignedNumber,
  formatUtcDateTime,
  toComparisonKey,
} from "./competitionPlayerPageUtils";

export const GradeBadge = ({ label }) => {
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

export const HeaderMetric = ({
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

export const AtGlanceItem = ({ label, value }) => (
  <div className="comp-player-glance-item">
    <dt className="comp-player-glance-label">{label}</dt>
    <dd className="comp-player-glance-value">
      <span className="font-data">{value}</span>
    </dd>
  </div>
);

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

export const RecentEventRow = ({ row, referenceMs }) => {
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

export const CompetitionPlayerHistoryTable = ({
  rows,
  referenceMs,
}) => (
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
            {rows.map((row) => (
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
                  {formatRelativeAge(row.eventMs, referenceMs)}
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
);

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

export const MatchImpactTable = ({
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

export const CompetitionPlayerBackLink = ({ to = "/" }) => (
  <Link to={to} className="comp-player-back-link">
    Back
  </Link>
);
