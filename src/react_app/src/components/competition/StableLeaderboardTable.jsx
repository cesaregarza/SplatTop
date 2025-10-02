import React, { forwardRef, memo, useEffect, useMemo, useRef, useState } from "react";
import { Virtuoso } from "react-virtuoso";
import {
  CRACKLE_PURPLE,
  chipClass,
  isXX,
  nf0,
  nf2,
  rateFor,
  severityOf,
  tierFor,
} from "./stableLeaderboardUtils";
import useMediaQuery from "../../hooks/useMediaQuery";

const GradeBadge = ({ label }) => {
  if (!label)
    return (
      <span
        className="grade-badge grade-tier-default"
        title="Grade not yet assigned for this player."
        aria-label="Grade not yet assigned"
      >
        —
      </span>
    );
  const tier = tierFor(label);
  const crackleClass = isXX(label) ? "crackle" : "";
  const dataProps = isXX(label)
    ? { "data-color": CRACKLE_PURPLE, "data-rate": rateFor(label) }
    : {};
  const tooltip = `Grade ${label}. Grades follow the XS → XX scale; higher tiers reflect stronger recent performance.`;
  return (
    <span
      className={`grade-badge ${tier} ${crackleClass}`}
      title={tooltip}
      aria-label={tooltip}
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
  let daysTitle = "We do not yet track inactivity risk for this player in the current window.";

  if (days != null) {
    severity = severityOf(days);
    if (days < 0) {
      daysLabel = "Inactive";
      daysTitle = "The player's ranked activity window has expired. They will drop until they play another ranked event.";
    } else if (days < 1) {
      daysLabel = "<1d";
      daysTitle = "Less than one day remains before this player becomes inactive.";
    } else {
      const rounded = Math.round(days);
      daysLabel = `${rounded}d`;
      daysTitle = `${rounded} day${rounded === 1 ? "" : "s"} until this player becomes inactive without a new ranked event.`;
    }
  } else if (windowCount != null && windowCount >= 3) {
    severity = "ok";
    daysLabel = "OK";
    daysTitle = "Player meets the ranked activity requirement; countdown resumes when they fall back to three events in the 120 day window.";
  } else if (windowCount == null || windowCount < 3) {
    daysLabel = "Not tracking";
    daysTitle = "Fewer than three ranked tournaments in the current window, so inactivity countdown is not tracked yet.";
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

  const scoreClasses = ["font-semibold", rankScoreClass, "font-data", "tabular-nums"];
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

const DESKTOP_MEDIA_QUERY = "(min-width: 768px)";
const MAX_TABLE_HEIGHT = 640;
const MIN_TABLE_HEIGHT = 320;
const ROW_HEIGHT_ESTIMATE = 68;
const DESKTOP_GRID_CLASS =
  "grid grid-cols-[5rem_minmax(16rem,1fr)_minmax(11rem,0.9fr)_7rem_minmax(10rem,0.9fr)_minmax(11rem,1fr)] gap-x-4";

const HEADER_HEIGHT_PX = 48;

const DesktopScroller = forwardRef(({ className, style, children, ...rest }, ref) => {
  const mergedClassName = [className, "max-h-full overflow-y-auto"].filter(Boolean).join(" ");
  return (
    <div ref={ref} className={mergedClassName} style={style} {...rest}>
      {children}
    </div>
  );
});

const DesktopHeader = ({ windowDays }) => {
  const windowLabel = windowDays ?? 120;
  return (
    <div
      className={`${DESKTOP_GRID_CLASS} z-20 bg-slate-900/70 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400 backdrop-blur rounded-t-lg border-b border-slate-800`}
    >
      <div title="Competitive rankings position after filtering">Rank</div>
      <div title="Player display name and Sendou ID">Player</div>
      <div title="Overall score that determines the player's leaderboard spot. Higher scores push players up the rankings.">
        Rank score
      </div>
      <div title="Grade tiers bundle players by score thresholds. XS and XX grades indicate top play.">Grade</div>
      <div title="Players drop after 120 days without a ranked event.">Days until inactive</div>
      <div title={`Ranked tournaments completed in the last ${windowLabel} days compared with lifetime total.`}>
        Tournaments
        <span className="ml-1 text-[0.65rem] font-semibold text-slate-500 tracking-wide">
          {windowLabel}d / Lifetime
        </span>
      </div>
    </div>
  );
};

const DesktopLeaderboardRow = ({ entry, isLast, isFirst, windowDays }) => {
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
    daysTitle,
    windowCount,
    windowCountClass,
    totalTournaments,
    highlightClass,
    scoreTitle,
    rankChangeLabel,
    rankChangeClass,
    rankChangeTitle,
    scoreChangeLabel,
    scoreChangeClass,
    scoreChangeTitle,
  } = entry;

  const baseClasses = [
    DESKTOP_GRID_CLASS,
    "items-start px-4 py-3 text-sm text-slate-200 transition hover:bg-slate-900/60",
    isLast ? "rounded-b-lg" : "border-b border-slate-800",
  ];

  if (highlightClass) {
    baseClasses.push("rounded-lg", highlightClass);
  }

  const style = isFirst ? { marginTop: HEADER_HEIGHT_PX } : undefined;

  const windowLabel = windowDays ?? 120;
  const windowDisplay = windowCount != null ? nf0.format(windowCount) : "—";
  const totalDisplay = totalTournaments != null ? nf0.format(totalTournaments) : "—";
  const tournamentsTitle = `Ranked tournaments in the last ${windowLabel} days versus lifetime total.`;

  return (
    <div className={baseClasses.filter(Boolean).join(" ")} style={style}>
      <div className="flex flex-col font-data tabular-nums text-slate-200 whitespace-nowrap">
        <span className="font-semibold text-slate-200">{rank}</span>
        {rankChangeLabel ? (
          <span
            className={`mt-1 text-[11px] font-semibold uppercase tracking-wide ${rankChangeClass}`}
            title={rankChangeTitle || undefined}
          >
            {rankChangeLabel}
          </span>
        ) : null}
      </div>

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
        <span
          className="mt-0.5 truncate text-xs text-slate-500 font-data"
          title={row.player_id || undefined}
        >
          {row.player_id || "—"}
        </span>
      </div>

      <div className="min-w-0">
        <div className={`${scoreClassName} flex items-baseline gap-2`} {...scoreDataProps} title={scoreTitle} aria-label={scoreTitle}>
          <span>{rankScoreDisplay}</span>
          {scoreChangeLabel ? (
            <span
              className={`text-xs font-semibold ${scoreChangeClass}`}
              title={scoreChangeTitle || undefined}
            >
              {scoreChangeLabel}
            </span>
          ) : null}
        </div>
        <ScoreBar value={rankScore} highlightClass={barHighlightClass} />
      </div>

      <div className="flex items-center">
        <GradeBadge label={grade} />
      </div>

      <div className="whitespace-nowrap" title={daysTitle}>
        <span
          className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium font-data ${chipClassName}`}
          aria-label={daysTitle}
        >
          {daysLabel}
        </span>
      </div>

      <div className="text-slate-200 whitespace-nowrap text-right" title={tournamentsTitle}>
        <span className={`font-data tabular-nums font-medium ${windowCountClass}`}>
          {windowDisplay}
        </span>
        <span className="mx-1 text-slate-500">/</span>
        <span className="font-data tabular-nums text-slate-400">{totalDisplay}</span>
      </div>
    </div>
  );
};

const DesktopLeaderboardTableView = ({
  rows,
  windowDays,
  virtuosoRef,
  page,
  pageCount,
  totalRows,
  pageRangeStart,
  pageRangeEnd,
  pageRealCount,
  onRequestPage,
}) => {
  if (!rows.length) return null;

  const estimatedHeight = Math.min(
    MAX_TABLE_HEIGHT,
    Math.max(MIN_TABLE_HEIGHT, 120 + rows.length * ROW_HEIGHT_ESTIMATE)
  );
  const viewportHeight = estimatedHeight + HEADER_HEIGHT_PX;

  return (
    <div className="relative rounded-lg border border-slate-800 bg-slate-950/60 shadow-md overflow-hidden">
      <div className="absolute inset-x-0 top-0 z-30">
        <DesktopHeader windowDays={windowDays} />
      </div>
      <Virtuoso
        ref={virtuosoRef}
        data={rows}
        overscan={8}
        style={{ height: viewportHeight }}
        components={{
          Scroller: DesktopScroller,
        }}
        itemContent={(index, entry) => (
          <DesktopLeaderboardRow
            entry={entry}
            isLast={index === rows.length - 1}
            isFirst={index === 0}
            windowDays={windowDays}
          />
        )}
      />
      <DesktopPaginationFooter
        page={page}
        pageCount={pageCount}
        totalRows={totalRows}
        pageRangeStart={pageRangeStart}
        pageRangeEnd={pageRangeEnd}
        pageRealCount={pageRealCount}
        onRequestPage={onRequestPage}
      />
    </div>
  );
};

const DesktopPaginationFooter = ({
  page = 1,
  pageCount = 1,
  totalRows = 0,
  pageRangeStart = 0,
  pageRangeEnd = 0,
  pageRealCount = 0,
  onRequestPage,
}) => {
  const safePage = Math.max(1, page);
  const safePageCount = Math.max(1, pageCount);
  const canPrev = safePage > 1;
  const canNext = safePage < safePageCount;
  const hasRange =
    totalRows > 0 && pageRealCount > 0 && pageRangeStart > 0 && pageRangeEnd >= pageRangeStart;

  const rangeStartLabel = hasRange ? nf0.format(pageRangeStart) : "—";
  const rangeEndLabel = hasRange ? nf0.format(pageRangeEnd) : "—";
  const totalLabel = totalRows > 0 ? nf0.format(totalRows) : "—";

  const [pageInput, setPageInput] = useState(String(safePage));

  useEffect(() => {
    setPageInput(String(safePage));
  }, [safePage]);

  if (totalRows <= 0 && pageRealCount <= 0) return null;

  const requestPage = (target) => {
    if (typeof onRequestPage === "function") {
      onRequestPage(target);
    }
  };

  const submitPage = () => {
    if (!pageInput.trim()) return;
    const parsed = Number(pageInput);
    if (!Number.isFinite(parsed)) return;
    const normalized = Math.min(Math.max(Math.floor(parsed), 1), safePageCount);
    if (normalized === safePage) return;
    requestPage(normalized);
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    submitPage();
  };

  return (
    <div className="border-t border-slate-800 bg-slate-900/60 px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
        <span className="font-data tabular-nums text-slate-300">
          Showing {hasRange ? `${rangeStartLabel}–${rangeEndLabel}` : "—"} of {totalLabel} players
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => requestPage(safePage - 1)}
            disabled={!canPrev}
            className="rounded-full border border-slate-800 bg-slate-950/80 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-slate-200 transition hover:bg-slate-900 disabled:opacity-50 disabled:hover:bg-slate-950/80"
          >
            Prev
          </button>
          <span className="text-xs uppercase tracking-wide text-slate-500">
            Page {safePage} / {safePageCount}
          </span>
          <form
            onSubmit={handleSubmit}
            className="flex items-center gap-1 rounded-full border border-slate-800 bg-slate-950/60 px-2 py-1 text-[11px] text-slate-400"
          >
            <label htmlFor="desktop-pagination-input" className="sr-only">
              Jump to page
            </label>
            <span>Jump to</span>
            <input
              id="desktop-pagination-input"
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              value={pageInput}
              onChange={(event) => setPageInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  submitPage();
                }
              }}
              onBlur={() => {
                if (!pageInput.trim()) {
                  setPageInput(String(safePage));
                }
              }}
              className="h-6 w-14 rounded bg-slate-900/80 px-2 text-center font-data text-slate-100 outline-none focus:ring-1 focus:ring-fuchsia-500/50"
            />
            <button
              type="submit"
              className="rounded bg-fuchsia-500/80 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white hover:bg-fuchsia-400"
            >
              Go
            </button>
          </form>
          <button
            type="button"
            onClick={() => requestPage(safePage + 1)}
            disabled={!canNext}
            className="rounded-full border border-slate-800 bg-slate-950/80 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-slate-200 transition hover:bg-slate-900 disabled:opacity-50 disabled:hover:bg-slate-950/80"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
};

const StableLeaderboardMobileList = ({
  rows,
  windowDays,
  page,
  pageCount,
  totalRows,
  pageRangeStart,
  pageRangeEnd,
  pageRealCount,
  onRequestPage,
  containerRef,
}) => {
  const windowLabel = windowDays ?? 120;

  if (!rows.length) return null;

  return (
    <div className="space-y-3" ref={containerRef}>
      <MobilePaginationControls
        page={page}
        pageCount={pageCount}
        totalRows={totalRows}
        pageRangeStart={pageRangeStart}
        pageRangeEnd={pageRangeEnd}
        pageRealCount={pageRealCount}
        onRequestPage={onRequestPage}
        className="mb-3"
      />
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
          daysTitle,
          windowCount,
          windowCountClass,
          totalTournaments,
          highlightClass,
          scoreTitle,
          rankChangeLabel,
          rankChangeClass,
          rankChangeTitle,
          scoreChangeLabel,
          scoreChangeClass,
          scoreChangeTitle,
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
                <span className="text-slate-100 font-data tabular-nums">{rank}</span>
                {rankChangeLabel ? (
                  <span
                    className={`ml-1 text-[11px] font-semibold ${rankChangeClass}`}
                    title={rankChangeTitle || undefined}
                  >
                    {rankChangeLabel}
                  </span>
                ) : null}
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
                <div
                  className="mt-1 truncate text-xs text-slate-500 font-data"
                  title={row.player_id || undefined}
                >
                  {row.player_id || "—"}
                </div>
              </div>
            </div>

            <div className="mt-3 space-y-1">
              <p className="text-xs uppercase tracking-wide text-slate-400">Rank Score</p>
              <div className={scoreClassName} {...scoreDataProps} title={scoreTitle} aria-label={scoreTitle}>
                {rankScoreDisplay}
              </div>
              {scoreChangeLabel ? (
                <div
                  className={`text-xs font-semibold font-data ${scoreChangeClass}`}
                  title={scoreChangeTitle || undefined}
                >
                  {scoreChangeLabel}
                </div>
              ) : null}
              <ScoreBar value={rankScore} highlightClass={barHighlightClass} />
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">Days until inactive</p>
                <span
                  className={`mt-1 inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium font-data ${chipClassName}`}
                  title={daysTitle}
                  aria-label={daysTitle}
                >
                  {daysLabel}
                </span>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">
                  Tournaments
                  <span className="ml-1 text-[0.65rem] font-semibold text-slate-500">
                    {windowLabel}d / Lifetime
                  </span>
                </p>
                <div className="mt-1 text-slate-100" title={`Ranked tournaments in the last ${windowLabel} days versus lifetime total.`}>
                  <span className={`font-semibold font-data tabular-nums ${windowCountClass}`}>
                    {windowCount != null ? nf0.format(windowCount) : "—"}
                  </span>
                  <span className="mx-1 text-slate-500">/</span>
                  <span className="font-data tabular-nums text-slate-400">
                    {totalTournaments != null ? nf0.format(totalTournaments) : "—"}
                  </span>
                </div>
              </div>
            </div>
          </article>
        );
      })}
      <MobilePaginationControls
        page={page}
        pageCount={pageCount}
        totalRows={totalRows}
        pageRangeStart={pageRangeStart}
        pageRangeEnd={pageRangeEnd}
        pageRealCount={pageRealCount}
        onRequestPage={onRequestPage}
      />
    </div>
  );
};

const MobilePaginationControls = ({
  page = 1,
  pageCount = 1,
  totalRows = 0,
  pageRangeStart = 0,
  pageRangeEnd = 0,
  pageRealCount = 0,
  onRequestPage,
  className = "",
}) => {
  const safePage = Math.max(1, page);
  const safePageCount = Math.max(1, pageCount);
  const canPrev = safePage > 1;
  const canNext = safePage < safePageCount;
  const hasRange =
    totalRows > 0 && pageRealCount > 0 && pageRangeStart > 0 && pageRangeEnd >= pageRangeStart;

  const rangeStartLabel = hasRange ? nf0.format(pageRangeStart) : "—";
  const rangeEndLabel = hasRange ? nf0.format(pageRangeEnd) : "—";
  const totalLabel = totalRows > 0 ? nf0.format(totalRows) : "—";

  const [pageInput, setPageInput] = useState(String(safePage));

  useEffect(() => {
    setPageInput(String(safePage));
  }, [safePage]);

  if (totalRows <= 0 && pageRealCount <= 0) return null;

  const requestPage = (target) => {
    if (typeof onRequestPage === "function") {
      onRequestPage(target);
    }
  };

  const submitPage = () => {
    if (!pageInput.trim()) return;
    const parsed = Number(pageInput);
    if (!Number.isFinite(parsed)) return;
    const normalized = Math.min(Math.max(Math.floor(parsed), 1), safePageCount);
    if (normalized === safePage) return;
    requestPage(normalized);
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    submitPage();
  };

  return (
    <div
      className={`${
        className ? `${className} ` : ""
      }rounded-lg border border-slate-800 bg-slate-900/70 px-4 py-3 text-sm text-slate-200`}
    >
      <div className="font-data tabular-nums text-slate-300">
        Showing {hasRange ? `${rangeStartLabel}–${rangeEndLabel}` : "—"} of {totalLabel} players
      </div>
      <div className="mt-3 flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => requestPage(safePage - 1)}
          disabled={!canPrev}
          className="flex-1 rounded-md border border-slate-800 bg-slate-950/80 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-100 transition hover:bg-slate-900 disabled:opacity-50 disabled:hover:bg-slate-950/80"
        >
          Prev
        </button>
        <span className="text-xs uppercase tracking-wide text-slate-500">
          Page {safePage} / {safePageCount}
        </span>
        <button
          type="button"
          onClick={() => requestPage(safePage + 1)}
          disabled={!canNext}
          className="flex-1 rounded-md border border-slate-800 bg-slate-950/80 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-100 transition hover:bg-slate-900 disabled:opacity-50 disabled:hover:bg-slate-950/80"
        >
          Next
        </button>
      </div>
      <form
        onSubmit={handleSubmit}
        className="mt-3 flex items-center justify-center gap-2 text-xs text-slate-400"
      >
        <label htmlFor="mobile-pagination-input" className="sr-only">
          Jump to page
        </label>
        <span>Jump to</span>
        <input
          id="mobile-pagination-input"
          type="text"
          inputMode="numeric"
          pattern="[0-9]*"
          value={pageInput}
          onChange={(event) => setPageInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              submitPage();
            }
          }}
          onBlur={() => {
            if (!pageInput.trim()) {
              setPageInput(String(safePage));
            }
          }}
          className="h-7 w-16 rounded bg-slate-950/80 px-2 text-center font-data text-slate-100 outline-none focus:ring-1 focus:ring-fuchsia-500/50"
        />
        <button
          type="submit"
          className="rounded bg-fuchsia-500/80 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-white hover:bg-fuchsia-400"
        >
          Go
        </button>
      </form>
    </div>
  );
};

const StableLeaderboardTable = ({
  rows,
  highlightId,
  windowDays,
  scrollResetKey,
  page,
  pageCount,
  totalRows,
  pageRangeStart,
  pageRangeEnd,
  pageRealCount,
  onRequestPage,
}) => {
  const preparedRows = useMemo(
    () => rows.map((row) => buildRowView(row, highlightId)),
    [rows, highlightId]
  );
  const virtuosoRef = useRef(null);
  const mobileContainerRef = useRef(null);
  const isDesktop = useMediaQuery(DESKTOP_MEDIA_QUERY);

  useEffect(() => {
    if (scrollResetKey === undefined || scrollResetKey === null) return;
    const handle = virtuosoRef.current;
    if (!handle?.scrollToIndex) return;
    try {
      handle.scrollToIndex({ index: 0, align: "start", behavior: "smooth" });
    } catch {
      /* no-op */
    }
  }, [scrollResetKey]);

  useEffect(() => {
    if (scrollResetKey === undefined || scrollResetKey === null) return;
    if (isDesktop) return;
    const node = mobileContainerRef.current;
    if (!node) return;
    try {
      node.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch {}
  }, [scrollResetKey, isDesktop]);

  return (
    <div className="space-y-4">
      {isDesktop ? (
        <DesktopLeaderboardTableView
          rows={preparedRows}
          windowDays={windowDays}
          virtuosoRef={virtuosoRef}
          page={page}
          pageCount={pageCount}
          totalRows={totalRows}
          pageRangeStart={pageRangeStart}
          pageRangeEnd={pageRangeEnd}
          pageRealCount={pageRealCount}
          onRequestPage={onRequestPage}
        />
      ) : (
        <StableLeaderboardMobileList
          rows={preparedRows}
          windowDays={windowDays}
          page={page}
          pageCount={pageCount}
          totalRows={totalRows}
          pageRangeStart={pageRangeStart}
          pageRangeEnd={pageRangeEnd}
          pageRealCount={pageRealCount}
          onRequestPage={onRequestPage}
          containerRef={mobileContainerRef}
        />
      )}
    </div>
  );
};

StableLeaderboardTable.displayName = "StableLeaderboardTable";

export default memo(StableLeaderboardTable);
