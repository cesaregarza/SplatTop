import React, { useEffect, useMemo, useRef, useState } from "react";
import CompetitionLayout from "./CompetitionLayout";

const DATE_FORMATTER = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});

const ROW_OPTIONS = [25, 50, 100];

const formatDate = (timestampMs) => {
  if (!timestampMs) return "—";
  try {
    return DATE_FORMATTER.format(new Date(timestampMs));
  } catch {
    return "—";
  }
};

const formatStrength = (strength) => {
  if (typeof strength !== "number" || !Number.isFinite(strength)) return "—";
  return strength.toFixed(2);
};

const nf0 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

const LoadingSkeleton = () => (
  <div className="rounded-lg border border-slate-800 bg-slate-950/60 shadow-md overflow-hidden">
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-800">
        <thead className="bg-slate-900/70 text-left text-xs font-semibold uppercase tracking-wider text-slate-400 border-b border-slate-800">
          <tr>
            <th className="px-4 py-3 w-16">#</th>
            <th className="px-4 py-3">Tournament</th>
            <th className="px-4 py-3">Date</th>
            <th className="px-4 py-3 text-right">Entrants</th>
            <th className="px-4 py-3 text-right">Strength</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {Array.from({ length: 10 }).map((_, index) => (
            <tr key={index} className="animate-pulse">
              <td className="px-4 py-3">
                <div className="h-4 w-6 rounded bg-slate-800" />
              </td>
              <td className="px-4 py-3">
                <div className="h-4 w-48 rounded bg-slate-800" />
              </td>
              <td className="px-4 py-3">
                <div className="h-4 w-24 rounded bg-slate-800" />
              </td>
              <td className="px-4 py-3">
                <div className="h-4 w-12 rounded bg-slate-800 ml-auto" />
              </td>
              <td className="px-4 py-3">
                <div className="h-4 w-16 rounded bg-slate-800 ml-auto" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

const RowsDropdown = ({ pageSize, onSelect }) => {
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const handleClick = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    const handleKey = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-2 rounded-md border border-slate-700 bg-slate-950/80 px-3 py-2 text-sm font-medium text-slate-100 shadow-sm transition hover:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-fuchsia-500/60"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="text-xs uppercase tracking-wide text-slate-400">Rows</span>
        <span className="font-data tabular-nums text-slate-100">{pageSize}</span>
        <span aria-hidden className="text-slate-500">▾</span>
      </button>
      {open && (
        <div className="absolute right-0 z-50 mt-2 w-36 rounded-lg border border-slate-800 bg-slate-950/95 p-1 shadow-xl backdrop-blur">
          {ROW_OPTIONS.map((size) => (
            <button
              key={size}
              type="button"
              onClick={() => { onSelect(size); setOpen(false); }}
              className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-sm transition hover:bg-slate-900 ${
                size === pageSize ? "bg-slate-900/70 text-slate-100" : "text-slate-200"
              }`}
            >
              <span className="font-data tabular-nums">{size}</span>
              <span className="text-xs uppercase tracking-wide text-slate-500">per page</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

const PaginationControls = ({ page, pageCount, totalRows, rangeStart, rangeEnd, onRequestPage }) => {
  const [pageInput, setPageInput] = useState(String(page));
  const safePage = Math.max(1, Math.min(page, pageCount));
  const safePageCount = Math.max(1, pageCount);
  const canPrev = safePage > 1;
  const canNext = safePage < safePageCount;

  useEffect(() => {
    setPageInput(String(safePage));
  }, [safePage]);

  const submitPage = () => {
    const parsed = parseInt(pageInput, 10);
    if (!Number.isFinite(parsed)) return;
    const normalized = Math.min(Math.max(Math.floor(parsed), 1), safePageCount);
    if (normalized !== safePage) onRequestPage(normalized);
  };

  return (
    <div className="border-t border-slate-800 bg-slate-900/60 px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
        <span className="font-data tabular-nums text-slate-300">
          Showing {rangeStart}–{rangeEnd} of {nf0.format(totalRows)} tournaments
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onRequestPage(safePage - 1)}
            disabled={!canPrev}
            className="rounded-full border border-slate-800 bg-slate-950/80 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-slate-200 transition hover:bg-slate-900 disabled:opacity-50 disabled:hover:bg-slate-950/80"
          >
            Prev
          </button>
          <span className="text-xs uppercase tracking-wide text-slate-500">
            Page {safePage} / {safePageCount}
          </span>
          <form
            onSubmit={(e) => { e.preventDefault(); submitPage(); }}
            className="flex items-center gap-1 rounded-full border border-slate-800 bg-slate-950/60 px-2 py-1 text-[11px] text-slate-400"
          >
            <span>Jump to</span>
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              value={pageInput}
              onChange={(e) => setPageInput(e.target.value)}
              onBlur={() => { if (!pageInput.trim()) setPageInput(String(safePage)); }}
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
            onClick={() => onRequestPage(safePage + 1)}
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

const TournamentStrengthPage = ({ snapshot, mainSiteUrl = "https://splat.top/" }) => {
  const { loading, error, disabled, tournaments, stable, danger, refresh } = snapshot;
  const [sortField, setSortField] = useState("strength");
  const [sortDesc, setSortDesc] = useState(true);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  useEffect(() => {
    const previous = document.title;
    document.title = "Tournament Strength - splat.top";
    return () => { document.title = previous; };
  }, []);

  const generatedAtMs = tournaments?.generated_at_ms ?? stable?.generated_at_ms ?? danger?.generated_at_ms ?? null;
  const stale = Boolean(tournaments?.stale || stable?.stale || danger?.stale);

  const filteredAndSorted = useMemo(() => {
    let rows = Array.isArray(tournaments?.data) ? [...tournaments.data] : [];

    // Filter by search query
    if (query.trim()) {
      const lowerQuery = query.toLowerCase().trim();
      rows = rows.filter((row) => {
        const name = (row.name || "").toLowerCase();
        const id = String(row.tournament_id || "").toLowerCase();
        return name.includes(lowerQuery) || id.includes(lowerQuery);
      });
    }

    // Sort
    rows.sort((a, b) => {
      let aVal, bVal;
      switch (sortField) {
        case "date":
          aVal = a.start_time_ms ?? 0;
          bVal = b.start_time_ms ?? 0;
          break;
        case "entrants":
          aVal = a.entrant_count ?? 0;
          bVal = b.entrant_count ?? 0;
          break;
        case "strength":
        default:
          aVal = a.strength ?? 0;
          bVal = b.strength ?? 0;
          break;
      }
      return sortDesc ? bVal - aVal : aVal - bVal;
    });

    return rows;
  }, [tournaments?.data, sortField, sortDesc, query]);

  // Reset to page 1 when filter/sort changes
  useEffect(() => {
    setPage(1);
  }, [query, sortField, sortDesc, pageSize]);

  const totalRows = filteredAndSorted.length;
  const pageCount = Math.max(1, Math.ceil(totalRows / pageSize));
  const safePage = Math.max(1, Math.min(page, pageCount));
  const rangeStart = totalRows > 0 ? (safePage - 1) * pageSize + 1 : 0;
  const rangeEnd = Math.min(safePage * pageSize, totalRows);
  const pagedRows = filteredAndSorted.slice((safePage - 1) * pageSize, safePage * pageSize);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDesc(!sortDesc);
    } else {
      setSortField(field);
      setSortDesc(true);
    }
  };

  const SortIndicator = ({ field }) => {
    if (sortField !== field) {
      return <span className="ml-1 text-slate-600">⇅</span>;
    }
    return <span className="ml-1 text-fuchsia-400">{sortDesc ? "↓" : "↑"}</span>;
  };

  if (disabled) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center px-6">
        <div className="max-w-lg text-center">
          <h1 className="text-3xl font-semibold">Tournament rankings disabled</h1>
          <p className="mt-4 text-slate-400">
            The tournament strength rankings are currently turned off. Check back later.
          </p>
        </div>
      </div>
    );
  }

  return (
    <CompetitionLayout
      generatedAtMs={generatedAtMs}
      stale={stale}
      loading={loading}
      onRefresh={refresh}
      faqLinkHref="/"
      faqLinkLabel="Leaderboard"
      vizLinkHref="/learn"
      vizLinkLabel="Interactive explainer"
      top500Href={mainSiteUrl}
    >
      {error && (
        <div className="mb-6 rounded-md border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {error}
        </div>
      )}

      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-slate-100">Tournament Strength</h2>
        <p className="mt-2 text-slate-400 text-sm">
          Ranked tournaments ordered by field strength (ln of top 20 player scores).
        </p>
      </div>

      {/* Controls */}
      <section className="mb-4 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-[220px]">
            <label className="sr-only" htmlFor="tournament-search">Search tournaments</label>
            <input
              id="tournament-search"
              type="search"
              placeholder="Search tournament…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full rounded-md bg-slate-950/70 pl-9 pr-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 ring-1 ring-white/10 focus:ring-2 focus:ring-fuchsia-500/60 outline-none"
            />
            <span className="pointer-events-none absolute left-3 top-2.5 text-slate-500" aria-hidden>
              🔎
            </span>
          </div>
          <RowsDropdown pageSize={pageSize} onSelect={setPageSize} />
        </div>
      </section>

      {loading && !pagedRows.length ? (
        <LoadingSkeleton />
      ) : (
        <div className="rounded-lg border border-slate-800 bg-slate-950/60 shadow-md overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-800">
              <thead className="bg-slate-900/70 sticky top-0 z-10 text-left text-xs font-semibold uppercase tracking-wider text-slate-400 backdrop-blur border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3 w-16 font-semibold">#</th>
                  <th className="px-4 py-3 font-semibold">Tournament</th>
                  <th
                    className="px-4 py-3 font-semibold cursor-pointer select-none hover:text-slate-200 transition"
                    onClick={() => handleSort("date")}
                  >
                    Date
                    <SortIndicator field="date" />
                  </th>
                  <th
                    className="px-4 py-3 font-semibold text-right cursor-pointer select-none hover:text-slate-200 transition"
                    onClick={() => handleSort("entrants")}
                  >
                    Entrants
                    <SortIndicator field="entrants" />
                  </th>
                  <th
                    className="px-4 py-3 font-semibold text-right cursor-pointer select-none hover:text-slate-200 transition"
                    onClick={() => handleSort("strength")}
                  >
                    Strength
                    <SortIndicator field="strength" />
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {pagedRows.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-slate-400">
                      {query ? "No tournaments match your search." : "No tournaments found."}
                    </td>
                  </tr>
                ) : (
                  pagedRows.map((row, idx) => (
                    <tr
                      key={row.tournament_id}
                      className="hover:bg-slate-800/40 transition-colors"
                    >
                      <td className="px-4 py-3 text-slate-500 tabular-nums font-medium">
                        {rangeStart + idx}
                      </td>
                      <td className="px-4 py-3">
                        <a
                          href={`https://sendou.ink/to/${row.tournament_id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-medium text-slate-100 hover:underline hover:text-fuchsia-200 transition-colors"
                          title={`View ${row.name || row.tournament_id} on sendou.ink`}
                        >
                          {row.name || row.tournament_id}
                        </a>
                      </td>
                      <td className="px-4 py-3 text-slate-300 tabular-nums">
                        {formatDate(row.start_time_ms)}
                      </td>
                      <td className="px-4 py-3 text-right text-slate-300 tabular-nums">
                        {row.entrant_count?.toLocaleString() ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-fuchsia-300 tabular-nums">
                        {formatStrength(row.strength)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          {totalRows > 0 && (
            <PaginationControls
              page={safePage}
              pageCount={pageCount}
              totalRows={totalRows}
              rangeStart={rangeStart}
              rangeEnd={rangeEnd}
              onRequestPage={setPage}
            />
          )}
        </div>
      )}
    </CompetitionLayout>
  );
};

export default TournamentStrengthPage;
