import React, { useEffect, useMemo, useRef, useState } from "react";

const nf2 = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 });

const RAW_GRADE_SCALE = [
  [-5, "XB-"],
  [-4, "XB"],
  [-3, "XB+"],
  [-2, "XA-"],
  [-1, "XA"],
  [0, "XA+"],
  [0.8, "XS-"],
  [1.5, "XS"],
  [2.4, "XS+"],
  [4, "XX"],
  [5, "XX+"],
  [Infinity, "XX★"],
];

const DISPLAY_GRADE_SCALE = RAW_GRADE_SCALE.map(([threshold, label]) => [
  threshold * 25 + 150,
  label,
]);

const gradeFor = (displayValue) => {
  for (const [threshold, label] of DISPLAY_GRADE_SCALE) {
    if (displayValue <= threshold) return label;
  }
  return "—";
};

const formatDate = (ms) => {
  if (!ms) return "—";
  const date = new Date(ms);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleDateString();
};

const severityOf = (days) => {
  if (days == null) return "neutral";
  if (days < 0) return "expired";
  if (days <= 0.25) return "critical";
  if (days <= 1) return "warn";
  if (days <= 3) return "watch";
  return "ok";
};

const chipClass = (severity) =>
  ({
    ok: "bg-emerald-500/10 text-emerald-200 ring-1 ring-emerald-400/15",
    watch: "bg-yellow-500/10 text-yellow-100 ring-1 ring-yellow-400/15",
    warn: "bg-amber-500/15 text-amber-200 ring-1 ring-amber-400/20",
    critical: "bg-rose-500/15 text-rose-300 ring-1 ring-rose-400/20",
    expired: "bg-rose-600/20 text-rose-200 ring-1 ring-rose-500/25",
    neutral: "bg-slate-700/20 text-slate-300 ring-1 ring-white/10",
  }[severity] || "bg-slate-700/20 text-slate-300 ring-1 ring-white/10");

const ScoreBar = ({ value, max }) => {
  if (value == null || max == null || max <= 0) return null;
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="mt-1 h-1.5 rounded-full bg-slate-800 overflow-hidden">
      <div className="h-full bg-fuchsia-500/60" style={{ width: `${pct}%` }} aria-hidden />
    </div>
  );
};

const StableLeaderboardView = ({ rows, loading, error }) => {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [jumpPlayerId, setJumpPlayerId] = useState("");
  const [jumpRank, setJumpRank] = useState("");
  const [highlightId, setHighlightId] = useState(null);
  const highlightTimerRef = useRef(null);

  const prepared = useMemo(() => {
    const data = Array.isArray(rows) ? rows : [];

    const mapped = data.map((row) => {
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

    filtered.sort(
      (a, b) => (a.stable_rank ?? Infinity) - (b.stable_rank ?? Infinity)
    );

    const maxShifted = filtered.reduce(
      (max, row) => (row._shifted != null && row._shifted > max ? row._shifted : max),
      0
    );

    const total = filtered.length;
    const pageCount = Math.max(1, Math.ceil(total / pageSize));
    const current = Math.min(page, pageCount);
    const start = (current - 1) * pageSize;
    const end = start + pageSize;
    const pageRows = filtered.slice(start, end);

    return { filtered: pageRows, total, pageCount, current, maxShifted, all: filtered };
  }, [rows, query, page, pageSize]);

  const goto = (value) => {
    setPage((current) => {
      const target = Math.max(1, Math.min(value, prepared.pageCount));
      return target;
    });
  };

  const gotoRank = (rankValue) => {
    const rankNum = Number(rankValue);
    if (!Number.isFinite(rankNum) || rankNum < 1) return;
    const index = rankNum - 1;
    const targetPage = Math.floor(index / pageSize) + 1;
    setQuery("");
    setPage(targetPage);
  };

  const gotoPlayerId = (pid) => {
    if (!pid) return;
    setQuery("");
    // Prefer stable_rank if available to compute exact index
    let idx = -1;
    try {
      const baseRow = (Array.isArray(rows) ? rows : []).find((r) => r.player_id === pid);
      if (baseRow && Number.isFinite(baseRow.stable_rank)) {
        idx = Number(baseRow.stable_rank) - 1;
      }
    } catch {}
    if (idx < 0) {
      // Fallback to current prepared list
      idx = prepared.all.findIndex((r) => r.player_id === pid);
    }
    if (idx >= 0) {
      const targetPage = Math.floor(idx / pageSize) + 1;
      setPage(targetPage);
      setHighlightId(pid);
      if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);
      highlightTimerRef.current = setTimeout(() => setHighlightId(null), 3000);
      // Update URL param for shareable link
      try {
        const url = new URL(window.location.href);
        url.searchParams.set("player", pid);
        url.searchParams.delete("rank");
        window.history.replaceState(null, "", url.toString());
      } catch {}
    }
  };

  // Deep-linking via ?player=ID or ?rank=N
  useEffect(() => {
    try {
      const url = new URL(window.location.href);
      const qPlayer = url.searchParams.get("player");
      const qRank = url.searchParams.get("rank");
      if (qPlayer) {
        gotoPlayerId(qPlayer);
      } else if (qRank) {
        gotoRank(qRank);
      }
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, pageSize]);

  const content = useMemo(() => {
    if (loading) {
      return (
        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="min-w-full divide-y divide-slate-800">
            <thead className="bg-slate-900/70 sticky top-0 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">
              <tr>
                <th className="px-4 py-3">Rank</th>
                <th className="px-4 py-3">Player</th>
                <th className="px-4 py-3">Display Score</th>
                <th className="px-4 py-3">Grade</th>
                <th className="px-4 py-3">Days Left</th>
                <th className="px-4 py-3">Next Expiry</th>
                <th className="px-4 py-3">Tournaments (90d)</th>
                <th className="px-4 py-3 hidden sm:table-cell">Last Active</th>
                <th className="px-4 py-3 hidden sm:table-cell">Last Tournament</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {Array.from({ length: 10 }).map((_, index) => (
                <tr key={index} className="animate-pulse">
                  <td className="px-4 py-3">
                    <div className="h-6 w-6 rounded-full bg-slate-800" />
                  </td>
                  <td className="px-4 py-3">
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
                    <div className="h-5 w-24 rounded bg-slate-800" />
                  </td>
                  <td className="px-4 py-3">
                    <div className="h-4 w-10 rounded bg-slate-800" />
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell">
                    <div className="h-4 w-24 rounded bg-slate-800" />
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell">
                    <div className="h-4 w-24 rounded bg-slate-800" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    if (error) {
      return (
        <div className="rounded-md border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          Unable to load the stable leaderboard right now: {error}
        </div>
      );
    }

    if (!prepared.total) {
      return (
        <p className="text-slate-400">
          {query
            ? "No players match your search."
            : "No players are available for this snapshot yet. Check back soon!"}
        </p>
      );
    }

    return (
      <>
        <div className="overflow-x-auto rounded-lg border border-slate-800 shadow-md">
          <table className="min-w-full divide-y divide-slate-800">
            <thead className="sticky top-0 z-10 bg-slate-900/70 backdrop-blur text-left text-xs font-semibold uppercase tracking-wider text-slate-400">
              <tr>
                <th className="px-4 py-3">Rank</th>
                <th className="px-4 py-3">Player</th>
                <th className="px-4 py-3">Display Score</th>
                <th className="px-4 py-3">Grade</th>
                <th className="px-4 py-3">Days Left</th>
                <th className="px-4 py-3">Next Expiry</th>
                <th className="px-4 py-3">Tournaments (90d)</th>
                <th className="px-4 py-3 hidden sm:table-cell">Last Active</th>
                <th className="px-4 py-3 hidden sm:table-cell">Last Tournament</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-sm">
              {prepared.filtered.map((row) => {
                const rank = row.stable_rank ?? "—";
                const shifted = row._shifted;
                const grade = row._grade;
                const tournamentCount =
                  row.window_tournament_count ?? row.tournament_count;
                const showDanger =
                  tournamentCount === 3 && row.danger_days_left != null;
                const days = showDanger ? row.danger_days_left : null;
                const severity = severityOf(days);
                const daysLabel =
                  days == null
                    ? "—"
                    : days < 0
                    ? "Expired"
                    : `${Math.max(days, 0).toFixed(1)}d`;
                const totalTournaments = row.tournament_count ?? null;
                const windowCount = row.window_tournament_count ?? null;

                const isHighlighted = highlightId && row.player_id === highlightId;
                return (
                  <tr
                    key={row.player_id}
                    className={`hover:bg-slate-900/60 ${
                      isHighlighted ? "ring-2 ring-fuchsia-500/40" : ""
                    }`}
                  >
                    <td className="px-4 py-3 font-semibold text-slate-200 whitespace-nowrap">{rank}</td>
                    <td className="px-4 py-3 align-top">
                      <div className="flex flex-col min-w-0 max-w-[14rem]">
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
                          className="text-xs text-slate-500 truncate"
                          title={row.player_id || undefined}
                        >
                          {row.player_id}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="font-semibold text-slate-100">
                        {shifted == null ? "—" : nf2.format(shifted)}
                      </div>
                      <div className="min-w-0">
                        <ScoreBar value={shifted} max={prepared.maxShifted} />
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="inline-flex items-center rounded-md bg-slate-800 px-2 py-0.5 text-xs font-semibold text-slate-200">
                        {grade}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${chipClass(severity)}`}>
                        {daysLabel}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-300">
                      {formatDate(showDanger ? row.danger_next_expiry_ms : null)}
                    </td>
                    <td className="px-4 py-3 text-slate-200 whitespace-nowrap">
                      {windowCount != null ? (
                        <div className="flex flex-col">
                          <span className="font-medium">{windowCount}</span>
                          {totalTournaments != null && (
                            <span className="text-xs text-slate-500">
                              total {totalTournaments}
                            </span>
                          )}
                        </div>
                      ) : (
                        totalTournaments ?? "—"
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-300 hidden sm:table-cell">
                      {formatDate(row.last_active_ms)}
                    </td>
                    <td className="px-4 py-3 text-slate-300 hidden sm:table-cell">
                      {formatDate(row.last_tournament_ms)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-4 flex flex-col items-center justify-between gap-3 sm:flex-row">
          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-400">
            <span>Rows per page</span>
            <select
              className="rounded-md bg-slate-900/80 px-2 py-1 text-slate-100 ring-1 ring-white/10"
              value={pageSize}
              onChange={(event) => {
                setPageSize(Number(event.target.value));
                setPage(1);
              }}
            >
              {[10, 25, 50, 100].map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
            <span className="ml-3">
              Page {prepared.current} of {prepared.pageCount} • {prepared.total} players
            </span>
          </div>
          <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto sm:items-center justify-center">
            <form
              className="flex items-center gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                gotoPlayerId(jumpPlayerId.trim());
              }}
            >
              <input
                type="text"
                inputMode="text"
                placeholder="Jump to player ID"
                value={jumpPlayerId}
                onChange={(e) => setJumpPlayerId(e.target.value)}
                className="rounded-md bg-slate-900/80 px-2 py-1 text-slate-100 placeholder:text-slate-500 ring-1 ring-white/10"
              />
              <button
                type="submit"
                className="rounded-md px-3 py-1.5 text-sm bg-fuchsia-600 text-white ring-1 ring-white/10 hover:bg-fuchsia-500"
              >
                Go
              </button>
            </form>

            <form
              className="flex items-center gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                gotoRank(jumpRank);
                // reflect in URL
                try {
                  const url = new URL(window.location.href);
                  url.searchParams.set("rank", String(jumpRank));
                  url.searchParams.delete("player");
                  window.history.replaceState(null, "", url.toString());
                } catch {}
              }}
            >
              <input
                type="number"
                inputMode="numeric"
                min="1"
                placeholder="Go to rank"
                value={jumpRank}
                onChange={(e) => setJumpRank(e.target.value)}
                className="rounded-md bg-slate-900/80 px-2 py-1 text-slate-100 placeholder:text-slate-500 ring-1 ring-white/10 w-28"
              />
              <button
                type="submit"
                className="rounded-md px-3 py-1.5 text-sm bg-slate-700 text-slate-100 ring-1 ring-white/10 hover:bg-slate-600"
              >
                Go
              </button>
            </form>

            <nav className="flex flex-wrap items-center justify-center gap-1">
              <button
                className="rounded-md px-3 py-1.5 text-sm bg-slate-900/70 ring-1 ring-white/10 text-slate-200 disabled:opacity-50"
                onClick={() => goto(prepared.current - 1)}
                disabled={prepared.current <= 1}
              >
                Prev
              </button>
              {(() => {
                const total = prepared.pageCount;
                const cur = prepared.current;
                const windowSize = 2; // pages around current
                const pages = new Set([1, total]);
                for (let p = cur - windowSize; p <= cur + windowSize; p++) {
                  if (p >= 1 && p <= total) pages.add(p);
                }
                const arr = Array.from(pages).sort((a, b) => a - b);
                const items = [];
                for (let i = 0; i < arr.length; i++) {
                  const p = arr[i];
                  const prev = i > 0 ? arr[i - 1] : null;
                  if (prev && p - prev > 1) {
                    items.push(
                      <span key={`gap-${prev}`} className="px-1 text-slate-500">
                        …
                      </span>
                    );
                  }
                  const active = p === cur;
                  items.push(
                    <button
                      key={p}
                      className={`rounded-md px-3 py-1.5 text-sm ring-1 ring-white/10 ${
                        active
                          ? "bg-slate-200 text-slate-900"
                          : "bg-slate-900/70 text-slate-200"
                      }`}
                      onClick={() => goto(p)}
                    >
                      {p}
                    </button>
                  );
                }
                return items;
              })()}
              <button
                className="rounded-md px-3 py-1.5 text-sm bg-slate-900/70 ring-1 ring-white/10 text-slate-200 disabled:opacity-50"
                onClick={() => goto(prepared.current + 1)}
                disabled={prepared.current >= prepared.pageCount}
              >
                Next
              </button>
            </nav>
          </div>
        </div>
      </>
    );
  }, [loading, error, prepared, query, pageSize]);

  return (
    <section>
      <header className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-100">Stable leaderboard</h2>
          <p className="mt-1 text-sm text-slate-400">
            Rankings only change when a player records a new tournament. Danger status is integrated below.
          </p>
        </div>
        <div className="w-full sm:w-80">
          <label className="sr-only" htmlFor="leaderboard-search">
            Search players
          </label>
          <div className="relative">
            <input
              id="leaderboard-search"
              type="text"
              placeholder="Search player or ID…"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setPage(1);
              }}
              className="w-full rounded-md bg-slate-900/70 pl-9 pr-3 py-2 text-slate-100 placeholder:text-slate-500 ring-1 ring-white/10 focus:ring-2 focus:ring-fuchsia-500/60 outline-none"
            />
            <span className="absolute left-3 top-2.5 text-slate-500">🔎</span>
          </div>
        </div>
      </header>

      {content}
    </section>
  );
};

export default StableLeaderboardView;
