import React, { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import "./StableLeaderboardView.css";
import useCrackleEffect from "../../hooks/useCrackleEffect";
import StableLeaderboardHeader from "./StableLeaderboardHeader";
import StableLeaderboardTable from "./StableLeaderboardTable";
import StableLeaderboardFooter from "./StableLeaderboardFooter";
import { createGradeShowcaseRows, gradeFor } from "./stableLeaderboardUtils";

const ENABLE_SHOWCASE_ROWS =
  String(process.env.REACT_APP_SHOWCASE_STABLE_LEADERBOARD ?? "true").toLowerCase() !== "false";
const SHOWCASE_ROWS = ENABLE_SHOWCASE_ROWS ? createGradeShowcaseRows() : [];

const LoadingSkeleton = memo(() => (
  <div className="overflow-x-auto rounded-lg border border-slate-800">
    <table className="min-w-full divide-y divide-slate-800">
      <thead className="bg-slate-900/70 sticky top-0 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">
        <tr>
          <th className="px-4 py-3">Rank</th>
          <th className="px-4 py-3 w-[16rem]">Player</th>
          <th className="px-4 py-3">Rank Score</th>
          <th className="px-4 py-3">Grade</th>
          <th className="px-4 py-3">Days Before Drop</th>
          <th className="px-4 py-3">Tournaments</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-800">
        {Array.from({ length: 10 }).map((_, index) => (
          <tr key={index} className="animate-pulse">
            <td className="px-4 py-3">
              <div className="h-6 w-6 rounded-full bg-slate-800" />
            </td>
            <td className="px-4 py-3 w-[16rem]">
              <div className="h-4 w-48 rounded bg-slate-800" />
              <div className="mt-1 h-3 w-28 rounded bg-slate-900" />
            </td>
            <td className="px-4 py-3">
              <div className="h-4 w-16 rounded bg-slate-800" />
              <div className="mt-1 h-1.5 w-32 rounded bg-slate-900" />
            </td>
            <td className="px-4 py-3">
              <div className="h-5 w-10 rounded bg-slate-800" />
            </td>
            <td className="px-4 py-3">
              <div className="h-5 w-16 rounded bg-slate-800" />
            </td>
            <td className="px-4 py-3">
              <div className="h-4 w-10 rounded bg-slate-800" />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
));

LoadingSkeleton.displayName = "StableLeaderboardLoadingSkeleton";

const ErrorBanner = memo(({ message }) => (
  <div className="rounded-md border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
    Unable to load the stable leaderboard right now: {message}
  </div>
));

ErrorBanner.displayName = "StableLeaderboardErrorBanner";

const EmptyState = memo(({ query }) => (
  <p className="text-slate-400">
    {query
      ? "No players match your search."
      : "No players are available for this snapshot yet. Check back soon!"}
  </p>
));

EmptyState.displayName = "StableLeaderboardEmptyState";

const StableLeaderboardView = ({ rows, loading, error, windowDays }) => {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [jumpPlayerId, setJumpPlayerId] = useState("");
  const [jumpGrade, setJumpGrade] = useState("");
  const [highlightId, setHighlightId] = useState(null);
  const highlightTimerRef = useRef(null);
  const rootRef = useRef(null);
  const footerRef = useRef(null);

  const prepared = useMemo(() => {
    const data = Array.isArray(rows) ? rows : [];
    const augmented = SHOWCASE_ROWS.length ? [...data, ...SHOWCASE_ROWS] : data;

    const mapped = augmented.map((row) => {
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
    });

    const q = query.trim().toLowerCase();
    const filtered = q
      ? mapped.filter(
          (row) =>
            row.display_name?.toLowerCase().includes(q) ||
            String(row.player_id ?? "").toLowerCase().includes(q)
        )
      : mapped.slice();

    filtered.sort((a, b) => (a.stable_rank ?? Infinity) - (b.stable_rank ?? Infinity));

    const total = filtered.length;
    const pageCount = Math.max(1, Math.ceil(total / pageSize));
    const current = Math.min(page, pageCount);
    const start = (current - 1) * pageSize;
    const end = start + pageSize;
    const pageRows = filtered.slice(start, end);

    return { filtered: pageRows, total, pageCount, current, all: filtered };
  }, [rows, query, page, pageSize]);

  const gotoPage = useCallback(
    (value) => {
      setPage((current) => {
        const target = Math.max(1, Math.min(value, prepared.pageCount));
        return target;
      });
    },
    [prepared.pageCount]
  );

  useCrackleEffect(rootRef, [rows, query, page, pageSize, jumpGrade]);

  const clearHighlightLater = useCallback(() => {
    if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);
    highlightTimerRef.current = setTimeout(() => setHighlightId(null), 3000);
  }, []);

  const gotoGrade = useCallback(
    (gradeValue) => {
      const label = String(gradeValue || "").trim();
      if (!label) return;
      const idx = prepared.all.findIndex((r) => r._grade === label);
    if (idx < 0) return;
    const targetPage = Math.floor(idx / pageSize) + 1;
    setQuery("");
    setPage(targetPage);
    try {
      const row = prepared.all[idx];
      if (row?.player_id) {
        setHighlightId(row.player_id);
        clearHighlightLater();
      }
      setJumpGrade(label);
      const url = new URL(window.location.href);
      url.searchParams.set("grade", label);
      url.searchParams.delete("player");
      url.searchParams.delete("rank");
      window.history.replaceState(null, "", url.toString());
      } catch {}
    },
    [prepared.all, pageSize, clearHighlightLater]
  );

  const gotoPlayerId = useCallback(
    (pid) => {
      if (!pid) return;
      setQuery("");
      let idx = -1;
    try {
      const baseRow = (Array.isArray(rows) ? rows : []).find((r) => r.player_id === pid);
      if (baseRow && Number.isFinite(baseRow.stable_rank)) {
        idx = Number(baseRow.stable_rank) - 1;
      }
    } catch {}
    if (idx < 0) {
      idx = prepared.all.findIndex((r) => r.player_id === pid);
    }
    if (idx >= 0) {
      const targetPage = Math.floor(idx / pageSize) + 1;
      setPage(targetPage);
      setHighlightId(pid);
      clearHighlightLater();
      try {
        const url = new URL(window.location.href);
        url.searchParams.set("player", pid);
        url.searchParams.delete("rank");
        window.history.replaceState(null, "", url.toString());
      } catch {}
      }
    },
    [rows, prepared.all, pageSize, clearHighlightLater]
  );

  useEffect(() => {
    try {
      const url = new URL(window.location.href);
      const qPlayer = url.searchParams.get("player");
      const qGrade = url.searchParams.get("grade");
      if (qPlayer) {
        gotoPlayerId(qPlayer);
      } else if (qGrade) {
        gotoGrade(qGrade);
      }
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, pageSize]);

  useEffect(() => () => {
    if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);
  }, []);

  const handlePageSizeChange = useCallback((size) => {
    setPageSize(size);
    setPage(1);
  }, []);

  const handleJumpPlayerSubmit = useCallback(
    (event) => {
      event.preventDefault();
      gotoPlayerId(jumpPlayerId.trim());
    },
    [gotoPlayerId, jumpPlayerId]
  );

  const handleQueryChange = useCallback((value) => {
    setQuery(value);
    setPage(1);
  }, []);

  const handleScrollToControls = useCallback(() => {
    try {
      footerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch {
      /* no-op */
    }
  }, []);

  let content;
  if (loading) {
    content = <LoadingSkeleton />;
  } else if (error) {
    content = <ErrorBanner message={error} />;
  } else if (!prepared.total) {
    content = <EmptyState query={query} />;
  } else {
    content = (
      <>
        <StableLeaderboardTable rows={prepared.filtered} highlightId={highlightId} windowDays={windowDays} />
        <StableLeaderboardFooter
          pageCount={prepared.pageCount}
          currentPage={prepared.current}
          totalPlayers={prepared.total}
          allRows={prepared.all}
          pageSize={pageSize}
          onPageSizeChange={handlePageSizeChange}
          onGotoPage={gotoPage}
          jumpGrade={jumpGrade}
          onGotoGrade={gotoGrade}
          jumpPlayerId={jumpPlayerId}
          onJumpPlayerChange={setJumpPlayerId}
          onJumpPlayerSubmit={handleJumpPlayerSubmit}
          ref={footerRef}
        />
      </>
    );
  }

  const showScrollButton = !loading && !error && prepared.total > 0;

  return (
    <section ref={rootRef}>
      <StableLeaderboardHeader
        query={query}
        onQueryChange={handleQueryChange}
        onScrollToControls={showScrollButton ? handleScrollToControls : undefined}
      />
      {content}
    </section>
  );
};

export default StableLeaderboardView;
