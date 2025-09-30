import React, { memo, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  CRACKLE_PURPLE,
  gradeChipClass,
  isXX,
  rateFor,
} from "./stableLeaderboardUtils";

const ROW_OPTIONS = [25, 50, 100];

const noop = () => {};

const useDismissibleMenu = (initialOpen = false) => {
  const [open, setOpen] = useState(initialOpen);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!open) return noop;

    const handleClick = (event) => {
      if (!containerRef.current) return;
      if (containerRef.current.contains(event.target)) return;
      setOpen(false);
    };

    const handleKey = (event) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  return { open, setOpen, containerRef };
};

const GradeDropdown = ({ grades, selectedGrade, onSelectGrade }) => {
  const { open, setOpen, containerRef } = useDismissibleMenu(false);
  const hasSelection = Boolean(selectedGrade);

  const toggle = () => setOpen((prev) => !prev);

  const handleSelect = (value) => {
    onSelectGrade(value);
    setOpen(false);
  };

  const renderChip = (label, isActive) => {
    const crackle = isXX(label);
    const chipClassName = `${gradeChipClass(label, isActive)} ${crackle ? "crackle" : ""}`.trim();
    const dataProps = crackle
      ? { "data-color": CRACKLE_PURPLE, "data-rate": rateFor(label) }
      : {};
    return (
      <span className={chipClassName} {...dataProps}>
        {label}
      </span>
    );
  };

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={toggle}
        className="inline-flex items-center gap-2 rounded-md border border-slate-700 bg-slate-950/80 px-3 py-2 text-sm font-medium text-slate-100 shadow-sm transition hover:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-fuchsia-500/60"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="text-xs uppercase tracking-wide text-slate-400">Grade filter</span>
        {hasSelection ? (
          renderChip(selectedGrade, true)
        ) : (
          <span className="rounded-full border border-slate-700 bg-slate-900/80 px-2 py-0.5 text-xs font-semibold text-slate-300">
            All
          </span>
        )}
        <span aria-hidden className="text-slate-500">
          ▾
        </span>
      </button>
      {open && (
        <div className="absolute right-0 z-50 mt-2 w-56 rounded-lg border border-slate-800 bg-slate-950/95 p-2 shadow-xl backdrop-blur">
          <div className="space-y-1">
            <button
              type="button"
              onClick={() => handleSelect("")}
              className={`flex w-full items-center justify-between gap-3 rounded-md px-3 py-2 text-sm transition hover:bg-slate-900 ${
                !hasSelection ? "bg-slate-900/70 text-slate-100" : "text-slate-300"
              }`}
              role="menuitemradio"
              aria-checked={!hasSelection}
            >
              <span>All grades</span>
              <span className="text-xs uppercase tracking-wide text-slate-500">Reset</span>
            </button>
            <div className="h-px bg-slate-800" />
            {grades.map((label) => {
              const active = label === selectedGrade;
              return (
                <button
                  key={label}
                  type="button"
                  onClick={() => handleSelect(label)}
                  className={`flex w-full items-center justify-between gap-3 rounded-md px-3 py-2 text-sm transition hover:bg-slate-900 ${
                    active ? "bg-slate-900/70 text-slate-100" : "text-slate-200"
                  }`}
                  role="menuitemradio"
                  aria-checked={active}
                >
                  <span className="font-medium">{label}</span>
                  {renderChip(label, active)}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

const RowsDropdown = ({ pageSize, rowOptions, onSelect }) => {
  const { open, setOpen, containerRef } = useDismissibleMenu(false);

  const toggle = () => setOpen((prev) => !prev);

  const handleSelect = (value) => {
    onSelect(value);
    setOpen(false);
  };

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={toggle}
        className="inline-flex items-center gap-2 rounded-md border border-slate-700 bg-slate-950/80 px-3 py-2 text-sm font-medium text-slate-100 shadow-sm transition hover:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-fuchsia-500/60"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="text-xs uppercase tracking-wide text-slate-400">Rows</span>
        <span className="font-data tabular-nums text-slate-100">{pageSize}</span>
        <span aria-hidden className="text-slate-500">
          ▾
        </span>
      </button>
      {open && (
        <div className="absolute right-0 z-50 mt-2 w-36 rounded-lg border border-slate-800 bg-slate-950/95 p-1 shadow-xl backdrop-blur">
          {rowOptions.map((size) => {
            const active = size === pageSize;
            return (
              <button
                key={size}
                type="button"
                onClick={() => handleSelect(size)}
                className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-sm transition hover:bg-slate-900 ${
                  active ? "bg-slate-900/70 text-slate-100" : "text-slate-200"
                }`}
                role="menuitemradio"
                aria-checked={active}
              >
                <span className="font-data tabular-nums">{size}</span>
                <span className="text-xs uppercase tracking-wide text-slate-500">per page</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

const StableLeaderboardControls = ({
  query,
  onQueryChange,
  grades,
  selectedGrade,
  onSelectGrade,
  pageSize,
  onPageSizeChange,
  onRefresh,
  refreshing,
}) => {
  const hasGrades = Array.isArray(grades) && grades.length > 0;
  const rowOptions = ROW_OPTIONS.includes(pageSize)
    ? ROW_OPTIONS
    : [...ROW_OPTIONS, pageSize].sort((a, b) => a - b);

  const handleQueryChange = (event) => {
    onQueryChange(event.target.value);
  };

  const handleGradeChange = (value) => {
    onSelectGrade(value);
  };

  const handlePageSizeChange = (value) => {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return;
    onPageSizeChange(numeric);
  };

  return (
    <section
      className="mb-4 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 shadow-sm"
      aria-label="Leaderboard controls"
    >
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[220px]">
          <label className="sr-only" htmlFor="stable-leaderboard-search">
            Search players
          </label>
          <input
            id="stable-leaderboard-search"
            type="search"
            placeholder="Search player or ID…"
            value={query}
            onChange={handleQueryChange}
            className="w-full rounded-md bg-slate-950/70 pl-9 pr-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 ring-1 ring-white/10 focus:ring-2 focus:ring-fuchsia-500/60 outline-none"
          />
          <span className="pointer-events-none absolute left-3 top-2.5 text-slate-500" aria-hidden>
            🔎
          </span>
        </div>

        {hasGrades && (
          <GradeDropdown
            grades={grades}
            selectedGrade={selectedGrade}
            onSelectGrade={handleGradeChange}
          />
        )}

        <RowsDropdown pageSize={pageSize} rowOptions={rowOptions} onSelect={handlePageSizeChange} />

        <Link
          to="/faq"
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-700 bg-slate-950/70 text-lg text-slate-200 transition hover:bg-slate-900"
          aria-label="How rankings work"
        >
          ?
        </Link>

        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-700 bg-slate-950/70 text-lg text-slate-200 transition hover:bg-slate-900 disabled:opacity-50"
            aria-label="Refresh snapshot"
            disabled={refreshing}
          >
            ⟳
          </button>
        )}
      </div>
    </section>
  );
};

StableLeaderboardControls.displayName = "StableLeaderboardControls";

export default memo(StableLeaderboardControls);
