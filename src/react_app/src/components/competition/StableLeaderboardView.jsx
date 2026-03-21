import React, { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./StableLeaderboardView.css";
import useCrackleEffect from "../../hooks/useCrackleEffect";
import useMediaQuery from "../../hooks/useMediaQuery";
import StableLeaderboardHeader from "./StableLeaderboardHeader";
import StableLeaderboardControls from "./StableLeaderboardControls";
import StableLeaderboardTable from "./StableLeaderboardTable";
import {
  getVisibleStableLeaderboardGrades,
  prepareStableLeaderboardRows,
} from "./stableLeaderboardViewModel";

const LoadingSkeleton = memo(() => (
  <div className="rounded-lg border border-slate-800 bg-slate-950/60 shadow-md overflow-hidden">
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-800">
        <thead
          className="bg-slate-900/70 sticky top-0 z-10 text-left text-xs font-semibold uppercase tracking-wider text-slate-400 backdrop-blur border-b border-slate-800"
          style={{ borderTopLeftRadius: "0.5rem", borderTopRightRadius: "0.5rem" }}
        >
          <tr>
            <th className="px-4 py-3 rounded-tl-lg">Rank</th>
            <th className="px-4 py-3 w-[16rem]">Player</th>
            <th className="px-4 py-3">Rank Score</th>
            <th className="px-4 py-3">Grade</th>
            <th className="px-4 py-3">Days Until Inactive</th>
            <th className="px-4 py-3 rounded-tr-lg">Tournaments 120d / Lifetime</th>
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

const StableLeaderboardView = ({ rows, loading, error, windowDays, onRefresh }) => {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [gradeFilter, setGradeFilter] = useState("");
  const [highlightId, setHighlightId] = useState(null);
  const [tableScrollKey, setTableScrollKey] = useState(0);
  const highlightTimerRef = useRef(null);
  const rootRef = useRef(null);
  const isDesktop = useMediaQuery("(min-width: 768px)");

  const prepared = useMemo(
    () =>
      prepareStableLeaderboardRows({
        rows,
        query,
        page,
        pageSize,
        gradeFilter,
      }),
    [rows, query, page, pageSize, gradeFilter]
  );

  const visibleGrades = useMemo(
    () => getVisibleStableLeaderboardGrades(prepared.availableGrades),
    [prepared.availableGrades]
  );

  const pageRangeStart = prepared.total === 0 ? 0 : (prepared.current - 1) * pageSize + 1;
  const pageRangeEnd = prepared.total === 0
    ? 0
    : Math.min(pageRangeStart + prepared.pageRealCount - 1, prepared.total);

  const scrollTableToTop = useCallback(() => {
    setTableScrollKey((key) => key + 1);
  }, []);

  const gotoPage = useCallback(
    (value) => {
      setPage((current) => {
        const target = Math.max(1, Math.min(value, prepared.pageCount));
        return target;
      });
    },
    [prepared.pageCount]
  );

  useCrackleEffect(rootRef, [rows, query, page, pageSize, gradeFilter, isDesktop]);

  const clearHighlightLater = useCallback(() => {
    if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);
    highlightTimerRef.current = setTimeout(() => setHighlightId(null), 3000);
  }, []);

  const applyGradeFilter = useCallback(
    (value, { scroll = true } = {}) => {
      const label = String(value || "").trim();
      setGradeFilter(label);
      setPage(1);
      setHighlightId(null);

      if (scroll) {
        scrollTableToTop();
      }

      if (typeof window !== "undefined") {
        try {
          const url = new URL(window.location.href);
          if (label) {
            url.searchParams.set("grade", label);
          } else {
            url.searchParams.delete("grade");
          }
          url.searchParams.delete("player");
          url.searchParams.delete("rank");
          window.history.replaceState(null, "", url.toString());
        } catch {}
      }
    },
    [scrollTableToTop]
  );

  const gotoPlayerId = useCallback(
    (pid) => {
      if (!pid) return;
      setQuery("");
      let idx = -1;
      try {
        const baseRow = (Array.isArray(rows) ? rows : []).find(
          (r) => r.player_id === pid
        );
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
      if (qGrade) {
        applyGradeFilter(qGrade, { scroll: false });
      }
      if (qPlayer) {
        gotoPlayerId(qPlayer);
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

  const handleSelectGrade = useCallback(
    (value) => {
      applyGradeFilter(value);
    },
    [applyGradeFilter]
  );

  const handleControlPageSizeChange = useCallback(
    (size) => {
      if (size === pageSize) return;
      scrollTableToTop();
      handlePageSizeChange(size);
    },
    [pageSize, scrollTableToTop, handlePageSizeChange]
  );

  const handlePageRequest = useCallback(
    (targetPage) => {
      scrollTableToTop();
      gotoPage(targetPage);
    },
    [scrollTableToTop, gotoPage]
  );

  const handleQueryChange = useCallback((value) => {
    setQuery(value);
    setPage(1);
  }, []);

  const handleSearchSubmit = useCallback(
    (rawValue) => {
      const needle = String(rawValue || "").trim().toLowerCase();
      if (!needle) return;
      const sourceRows = Array.isArray(rows) ? rows : [];
      const exactPlayerMatch = sourceRows.find(
        (row) => String(row.player_id || "").toLowerCase() === needle
      );
      const prefixNameMatch = sourceRows.find((row) =>
        String(row.display_name || "").toLowerCase().startsWith(needle)
      );
      const target = exactPlayerMatch || prefixNameMatch;
      if (!target?.player_id) return;
      navigate(`/u/${target.player_id}`);
    },
    [rows, navigate]
  );

  let content;
  if (loading) {
    content = <LoadingSkeleton />;
  } else if (error) {
    content = <ErrorBanner message={error} />;
  } else if (!prepared.total && !prepared.hasShowcase) {
    content = <EmptyState query={query} />;
  } else {
    content = (
      <StableLeaderboardTable
        rows={prepared.filtered}
        highlightId={highlightId}
        windowDays={windowDays}
        scrollResetKey={tableScrollKey}
        page={prepared.current}
        pageCount={prepared.pageCount}
        totalRows={prepared.total}
        pageRangeStart={pageRangeStart}
        pageRangeEnd={pageRangeEnd}
        pageRealCount={prepared.pageRealCount}
        onRequestPage={handlePageRequest}
      />
    );
  }

  return (
    <section ref={rootRef}>
      <StableLeaderboardHeader />
      <StableLeaderboardControls
        query={query}
        onQueryChange={handleQueryChange}
        onSearchSubmit={handleSearchSubmit}
        grades={visibleGrades}
        selectedGrade={gradeFilter}
        onSelectGrade={handleSelectGrade}
        pageSize={pageSize}
        onPageSizeChange={handleControlPageSizeChange}
        onRefresh={onRefresh}
        refreshing={loading}
      />
      {content}
    </section>
  );
};

export default StableLeaderboardView;
