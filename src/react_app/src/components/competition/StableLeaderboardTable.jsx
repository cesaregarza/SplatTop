import React, { memo, useMemo } from "react";
import {
  CRACKLE_PURPLE,
  chipClass,
  isXX,
  nf2,
  rateFor,
  severityOf,
  tierFor,
} from "./stableLeaderboardUtils";

const GradeBadge = ({ label }) => {
  if (!label)
    return (
      <span className="grade-badge grade-tier-default" title="Grade —">
        —
      </span>
    );
  const tier = tierFor(label);
  const crackleClass = isXX(label) ? "crackle" : "";
  const dataProps = isXX(label)
    ? { "data-color": CRACKLE_PURPLE, "data-rate": rateFor(label) }
    : {};
  return (
    <span
      className={`grade-badge ${tier} ${crackleClass}`}
      title={`Grade ${label}`}
      {...dataProps}
    >
      {label}
    </span>
  );
};

const ScoreBar = ({ value, highlightClass = "" }) => {
  if (value == null) return null;
  const BASELINE_MAX = 250;
  const pct = Math.max(0, Math.min(100, (value / BASELINE_MAX) * 100));
  const tier = value >= 300 ? "xxstar" : value >= BASELINE_MAX ? "xxplus" : "base";
  const wrapperClasses = ["relative mt-1 h-1.5 rounded-full bg-slate-800 overflow-hidden"];
  let wrapperStyle;
  let barClass = "bg-fuchsia-500/60";
  let glow = null;

  if (tier === "xxplus") {
    wrapperClasses.push("ring-1 ring-fuchsia-300/40");
    barClass = "bg-gradient-to-r from-fuchsia-400 via-violet-300 to-fuchsia-300";
    glow = (
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 rounded-full bg-fuchsia-400/25 blur-sm"
      />
    );
  } else if (tier === "xxstar") {
    wrapperClasses.push("ring-1 ring-amber-200/40");
    wrapperStyle = { boxShadow: "0 0 12px rgba(249, 168, 212, 0.35)" };
    barClass = "bg-gradient-to-r from-fuchsia-300 via-violet-200 to-amber-200";
    glow = (
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 rounded-full bg-amber-100/30 blur"
      />
    );
  }

  if (highlightClass) wrapperClasses.push(highlightClass);

  return (
    <div className={wrapperClasses.join(" ")} style={wrapperStyle}>
      <div className={`h-full ${barClass}`} style={{ width: `${pct}%` }} aria-hidden />
      {glow}
    </div>
  );
};

const buildRowView = (row, highlightId) => {
  const rank = row.stable_rank ?? "—";
  const grade = row._grade;
  const rankScore = row._shifted ?? null;
  const windowCount = row.window_tournament_count ?? null;
  const totalTournaments = row.tournament_count ?? null;
  const showDanger = windowCount === 3 && row.danger_days_left != null;
  const days = showDanger ? row.danger_days_left : null;
  const severity = severityOf(days);
  const chipClassName = chipClass(severity);
  let daysLabel = "—";
  if (days != null) {
    if (days < 0) {
      daysLabel = "Expired";
    } else if (days < 1) {
      daysLabel = "<1d";
    } else {
      daysLabel = `${Math.round(days)}d`;
    }
  }

  const rankScoreClass =
    rankScore == null
      ? "text-slate-100"
      : rankScore >= 300
      ? "text-amber-100"
      : rankScore >= 250
      ? "text-fuchsia-200"
      : "text-slate-100";

  const scoreClasses = ["font-semibold", rankScoreClass, "font-data"];
  const scoreDataProps = {};
  const showScoreHighlight = grade === "XX★";
  if (showScoreHighlight) {
    scoreClasses.push("xxstar-score", "crackle");
    scoreDataProps["data-color"] = CRACKLE_PURPLE;
    scoreDataProps["data-rate"] = 9;
  }

  const highlighted = Boolean(highlightId && row.player_id === highlightId);
  const highlightClass = highlighted
    ? "ring-2 ring-fuchsia-500/40 ring-offset-0"
    : "";

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
    windowCount,
    totalTournaments,
    highlighted,
    highlightClass,
  };
};

const StableLeaderboardMobileList = ({ rows, windowDays }) => {
  const windowLabel = windowDays ?? 90;

  if (!rows.length) return null;

  return (
    <div className="md:hidden space-y-3">
      {rows.map((entry) => {
        const { row, rank, grade, rankScore, rankScoreDisplay, scoreClassName, scoreDataProps, barHighlightClass, chipClassName, daysLabel, windowCount, totalTournaments, highlightClass } = entry;
        const key = row.player_id || `${row.display_name || "player"}-${rank}`;
        return (
          <article
            key={key}
            className={`rounded-xl border border-slate-800 bg-slate-900/75 p-4 shadow-sm transition ${highlightClass}`.trim()}
          >
            <div className="flex items-center justify-between gap-3">
              <span className="inline-flex items-center rounded-full bg-slate-800/80 px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide text-slate-300">
                Rank <span className="font-data text-slate-100">{rank}</span>
              </span>
              <GradeBadge label={grade} />
            </div>

            <div className="mt-3 flex items-start justify-between gap-3">
              <div className="min-w-0">
                {row.player_id ? (
                  <a
                    href={`https://sendou.ink/u/${row.player_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-base font-semibold text-slate-100 truncate hover:underline"
                    title={row.display_name || undefined}
                  >
                    {row.display_name}
                  </a>
                ) : (
                  <span className="text-base font-semibold text-slate-100 truncate" title={row.display_name || undefined}>
                    {row.display_name}
                  </span>
                )}
                <div className="text-xs text-slate-500 truncate font-data" title={row.player_id || undefined}>
                  {row.player_id || "—"}
                </div>
              </div>
            </div>

            <div className="mt-3 space-y-1">
              <p className="text-xs uppercase tracking-wide text-slate-400">Rank Score</p>
              <div className={scoreClassName} {...scoreDataProps}>
                {rankScoreDisplay}
              </div>
              <ScoreBar value={rankScore} highlightClass={barHighlightClass} />
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">Danger Status</p>
                <span className={`mt-1 inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium font-data ${chipClassName}`}>
                  {daysLabel}
                </span>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">Tournaments (last {windowLabel}d)</p>
                {windowCount != null ? (
                  <div className="mt-1">
                    <span className="font-semibold text-slate-100 font-data">{windowCount}</span>
                    {totalTournaments != null && (
                      <div className="text-xs text-slate-500">
                        total <span className="font-data">{totalTournaments}</span>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="mt-1 text-slate-100 font-data">{totalTournaments ?? "—"}</div>
                )}
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
};

const StableLeaderboardTable = ({ rows, highlightId, windowDays }) => {
  const preparedRows = useMemo(
    () => rows.map((row) => buildRowView(row, highlightId)),
    [rows, highlightId]
  );

  return (
    <div className="space-y-4">
      <div className="hidden md:block">
        <div className="overflow-x-auto rounded-lg border border-slate-800 shadow-md">
          <table className="min-w-full divide-y divide-slate-800">
            <thead className="sticky top-0 z-10 bg-slate-900/70 backdrop-blur text-left text-xs font-semibold uppercase tracking-wider text-slate-400">
              <tr>
                <th className="px-4 py-3" title="Competitive rankings position after filtering">Rank</th>
                <th className="px-4 py-3 w-[16rem]" title="Player display name and Sendou ID">Player</th>
                <th
                  className="px-4 py-3"
                  title="Overall score that determines the player's leaderboard spot."
                >
                  Rank Score
                </th>
                <th className="px-4 py-3" title="Grade tier derived from the current rank score">Grade</th>
                <th className="px-4 py-3" title="Days until the player could fall off the leaderboard">Days Before Drop</th>
                <th
                  className="px-4 py-3"
                  title={`Tournaments played in the last ${windowDays ?? 90} days; total lifetime shown beneath when available.`}
                >
                  Tournaments (Last {windowDays ?? 90} Days)
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-sm">
              {preparedRows.map((entry) => {
                const {
                  row,
                  rank,
                  grade,
                  rankScore,
                  rankScoreDisplay,
                  scoreClassName,
                  scoreDataProps,
                  barHighlightClass,
                  chipClassName,
                  daysLabel,
                  windowCount,
                  totalTournaments,
                  highlightClass,
                } = entry;

                const key = row.player_id || `${row.display_name || "player"}-${rank}`;

                return (
                  <tr
                    key={key}
                    className={`hover:bg-slate-900/60 ${highlightClass}`.trim()}
                  >
                    <td className="px-4 py-3 font-semibold text-slate-200 whitespace-nowrap font-data">{rank}</td>
                    <td className="px-4 py-3 align-top w-[16rem]">
                      <div className="flex flex-col min-w-0 w-[16rem]">
                        {row.player_id ? (
                          <a
                            href={`https://sendou.ink/u/${row.player_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-medium text-slate-100 truncate hover:underline"
                            title={row.display_name || undefined}
                          >
                            {row.display_name}
                          </a>
                        ) : (
                          <span
                            className="font-medium text-slate-100 truncate"
                            title={row.display_name || undefined}
                          >
                            {row.display_name}
                          </span>
                        )}
                        <span className="text-xs text-slate-500 truncate font-data" title={row.player_id || undefined}>
                          {row.player_id}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className={scoreClassName} {...scoreDataProps}>
                        {rankScoreDisplay}
                      </div>
                      <div className="min-w-0">
                        <ScoreBar value={rankScore} highlightClass={barHighlightClass} />
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <GradeBadge label={grade} />
                    </td>
                    <td
                      className="px-4 py-3 whitespace-nowrap"
                      title="Days until this player could fall off the leaderboard"
                    >
                      <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium font-data ${chipClassName}`}>
                        {daysLabel}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-200 whitespace-nowrap">
                      {windowCount != null ? (
                        <div className="flex flex-col">
                          <span className="font-medium font-data">{windowCount}</span>
                          {totalTournaments != null && (
                            <span className="text-xs text-slate-500">
                              total <span className="font-data">{totalTournaments}</span>
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="font-data">{totalTournaments ?? "—"}</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <StableLeaderboardMobileList rows={preparedRows} windowDays={windowDays} />
    </div>
  );
};

StableLeaderboardTable.displayName = "StableLeaderboardTable";

export default memo(StableLeaderboardTable);
