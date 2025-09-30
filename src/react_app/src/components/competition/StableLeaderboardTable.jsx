import React, { forwardRef, memo, useMemo } from "react";
import { Virtuoso } from "react-virtuoso";
import {
  CRACKLE_PURPLE,
  chipClass,
  isXX,
  nf2,
  rateFor,
  severityOf,
  tierFor,
} from "./stableLeaderboardUtils";
import useMediaQuery from "../../hooks/useMediaQuery";

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

const DESKTOP_MEDIA_QUERY = "(min-width: 768px)";
const MAX_TABLE_HEIGHT = 640;
const MIN_TABLE_HEIGHT = 320;
const ROW_HEIGHT_ESTIMATE = 68;
const DESKTOP_GRID_CLASS =
  "grid grid-cols-[5rem_minmax(16rem,1fr)_minmax(11rem,0.9fr)_7rem_minmax(10rem,0.9fr)_minmax(11rem,1fr)] gap-x-4";

const DesktopScroller = forwardRef((props, ref) => (
  <div
    {...props}
    ref={ref}
    className={[props.className, "max-h-full overflow-y-auto"].filter(Boolean).join(" ")}
  />
));

const DesktopHeader = ({ windowDays }) => (
  <div
    className={`${DESKTOP_GRID_CLASS} sticky top-0 z-10 bg-slate-900/70 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400 backdrop-blur`}
  >
    <div title="Competitive rankings position after filtering">Rank</div>
    <div title="Player display name and Sendou ID">Player</div>
    <div title="Overall score that determines the player's leaderboard spot.">Rank Score</div>
    <div title="Grade tier derived from the current rank score">Grade</div>
    <div title="Days until the player could fall off the leaderboard">Days Before Drop</div>
    <div
      title={`Tournaments played in the last ${windowDays ?? 90} days; total lifetime shown beneath when available.`}
    >
      Tournaments (Last {windowDays ?? 90} Days)
    </div>
  </div>
);

const DesktopLeaderboardRow = ({ entry, isLast }) => {
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

  const baseClasses = [
    DESKTOP_GRID_CLASS,
    "items-start px-4 py-3 text-sm text-slate-200 transition hover:bg-slate-900/60",
    isLast ? "" : "border-b border-slate-800",
  ];

  if (highlightClass) {
    baseClasses.push("rounded-lg", highlightClass);
  }

  return (
    <div className={baseClasses.filter(Boolean).join(" ")}>
      <div className="font-semibold font-data text-slate-200 whitespace-nowrap">{rank}</div>

      <div className="min-w-0 flex flex-col">
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

      <div className="min-w-0">
        <div className={scoreClassName} {...scoreDataProps}>
          {rankScoreDisplay}
        </div>
        <ScoreBar value={rankScore} highlightClass={barHighlightClass} />
      </div>

      <div className="flex items-center">
        <GradeBadge label={grade} />
      </div>

      <div className="whitespace-nowrap" title="Days until this player could fall off the leaderboard">
        <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium font-data ${chipClassName}`}>
          {daysLabel}
        </span>
      </div>

      <div className="text-slate-200 whitespace-nowrap">
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
      </div>
    </div>
  );
};

const DesktopLeaderboardTableView = ({ rows, windowDays }) => {
  if (!rows.length) return null;

  const estimatedHeight = Math.min(
    MAX_TABLE_HEIGHT,
    Math.max(MIN_TABLE_HEIGHT, 120 + rows.length * ROW_HEIGHT_ESTIMATE)
  );

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 shadow-md">
      <Virtuoso
        data={rows}
        overscan={8}
        style={{ height: estimatedHeight }}
        components={{
          Header: () => <DesktopHeader windowDays={windowDays} />,
          Scroller: DesktopScroller,
        }}
        itemContent={(index, entry) => (
          <DesktopLeaderboardRow
            entry={entry}
            isLast={index === rows.length - 1}
          />
        )}
      />
    </div>
  );
};

const StableLeaderboardMobileList = ({ rows, windowDays }) => {
  const windowLabel = windowDays ?? 90;

  if (!rows.length) return null;

  return (
    <div className="space-y-3">
      {rows.map((entry) => {
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
        const cardClasses = [
          "rounded-xl border border-slate-800 bg-slate-900/75 p-4 shadow-sm transition",
          highlightClass,
        ]
          .filter(Boolean)
          .join(" ");

        return (
          <article key={key} className={cardClasses}>
            <div className="flex items-center justify-between gap-3">
              <span className="inline-flex items-baseline gap-1 rounded-full bg-slate-800/80 px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide text-slate-300">
                <span>Rank</span>
                <span className="text-slate-100">{rank}</span>
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
                  <span
                    className="text-base font-semibold text-slate-100 truncate"
                    title={row.display_name || undefined}
                  >
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
  const isDesktop = useMediaQuery(DESKTOP_MEDIA_QUERY);

  return (
    <div className="space-y-4">
      {isDesktop ? (
        <DesktopLeaderboardTableView rows={preparedRows} windowDays={windowDays} />
      ) : (
        <StableLeaderboardMobileList rows={preparedRows} windowDays={windowDays} />
      )}
    </div>
  );
};

StableLeaderboardTable.displayName = "StableLeaderboardTable";

export default memo(StableLeaderboardTable);
