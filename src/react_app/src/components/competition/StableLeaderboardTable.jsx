import React from "react";
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

const ScoreBar = ({ value }) => {
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

  return (
    <div className={wrapperClasses.join(" ")} style={wrapperStyle}>
      <div className={`h-full ${barClass}`} style={{ width: `${pct}%` }} aria-hidden />
      {glow}
    </div>
  );
};

const StableLeaderboardTable = ({ rows, highlightId, windowDays }) => (
  <div className="overflow-x-auto rounded-lg border border-slate-800 shadow-md">
    <table className="min-w-full divide-y divide-slate-800">
      <thead className="sticky top-0 z-10 bg-slate-900/70 backdrop-blur text-left text-xs font-semibold uppercase tracking-wider text-slate-400">
        <tr>
          <th className="px-4 py-3" title="Stable leaderboard position after filtering">Rank</th>
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
        {rows.map((row) => {
          const rank = row.stable_rank ?? "—";
          const shifted = row._shifted;
          const grade = row._grade;
          const tournamentCount = row.window_tournament_count ?? null;
          const showDanger = tournamentCount === 3 && row.danger_days_left != null;
          const days = showDanger ? row.danger_days_left : null;
          const severity = severityOf(days);
          const rankScore = shifted;
          const rankScoreClass =
            rankScore == null
              ? "text-slate-100"
              : rankScore >= 300
              ? "text-amber-100"
              : rankScore >= 250
              ? "text-fuchsia-200"
              : "text-slate-100";
          let daysLabel;
          if (days == null) {
            daysLabel = "—";
          } else if (days < 0) {
            daysLabel = "Expired";
          } else if (days < 1) {
            daysLabel = "<1d";
          } else {
            daysLabel = `${Math.round(days)}d`;
          }
          const totalTournaments = row.tournament_count ?? null;
          const windowCount = row.window_tournament_count ?? null;
          const isHighlighted = highlightId && row.player_id === highlightId;

          return (
            <tr
              key={row.player_id}
              className={`hover:bg-slate-900/60 ${isHighlighted ? "ring-2 ring-fuchsia-500/40" : ""}`}
            >
              <td className="px-4 py-3 font-semibold text-slate-200 whitespace-nowrap">{rank}</td>
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
                  <span className="text-xs text-slate-500 truncate" title={row.player_id || undefined}>
                    {row.player_id}
                  </span>
                </div>
              </td>
              <td className="px-4 py-3 whitespace-nowrap">
                <div className={`font-semibold ${rankScoreClass}`}>
                  {rankScore == null ? "—" : nf2.format(rankScore)}
                </div>
                <div className="min-w-0">
                  <ScoreBar value={rankScore} />
                </div>
              </td>
              <td className="px-4 py-3 whitespace-nowrap">
                <GradeBadge label={grade} />
              </td>
              <td
                className="px-4 py-3 whitespace-nowrap"
                title="Days until this player could fall off the leaderboard"
              >
                <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${chipClass(severity)}`}>
                  {daysLabel}
                </span>
              </td>
              <td className="px-4 py-3 text-slate-200 whitespace-nowrap">
                {windowCount != null ? (
                  <div className="flex flex-col">
                    <span className="font-medium">{windowCount}</span>
                    {totalTournaments != null && (
                      <span className="text-xs text-slate-500">total {totalTournaments}</span>
                    )}
                  </div>
                ) : (
                  totalTournaments ?? "—"
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  </div>
);

export default StableLeaderboardTable;
