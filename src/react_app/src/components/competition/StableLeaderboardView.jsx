import React, { useEffect, useMemo, useRef, useState } from "react";
import "./StableLeaderboardView.css";

const CRACKLE_PURPLE = "#a78bfa";
const nf2 = new Intl.NumberFormat(undefined, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

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

// Map grade labels to CSS tier classes for consistent styling
const tierFor = (label) => {
  switch (label) {
    case "XX★":
      return "grade-tier-xxstar";
    case "XX+":
      return "grade-tier-xxplus";
    case "XX":
      return "grade-tier-xx";
    case "XS+":
      return "grade-tier-xsplus";
    case "XS":
      return "grade-tier-xs";
    case "XS-":
      return "grade-tier-xsminus";
    case "XA+":
      return "grade-tier-xaplus";
    case "XA":
      return "grade-tier-xa";
    case "XA-":
      return "grade-tier-xaminus";
    case "XB+":
      return "grade-tier-xbplus";
    case "XB":
      return "grade-tier-xb";
    case "XB-":
      return "grade-tier-xbminus";
    default:
      return "grade-tier-default";
  }
};

const gradeChipClass = (label, active) => {
  const tier = tierFor(label);
  return `grade-chip ${tier} ${active ? "is-active" : ""}`.trim();
};

const isXX = (label) => label === "XX★" || label === "XX+" || label === "XX";
const rateFor = (label) => (label === "XX★" ? 4 : label === "XX+" ? 3 : 2.4);

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
  const wrapperClasses = [
    "relative mt-1 h-1.5 rounded-full bg-slate-800 overflow-hidden"
  ];
  let wrapperStyle = undefined;
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

const StableLeaderboardView = ({ rows, loading, error, windowDays }) => {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [jumpPlayerId, setJumpPlayerId] = useState("");
  const [jumpGrade, setJumpGrade] = useState("");
  const [highlightId, setHighlightId] = useState(null);
  const highlightTimerRef = useRef(null);
  const rootRef = useRef(null);
  const crackleMapRef = useRef(new Map());

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

    const total = filtered.length;
    const pageCount = Math.max(1, Math.ceil(total / pageSize));
    const current = Math.min(page, pageCount);
    const start = (current - 1) * pageSize;
    const end = start + pageSize;
    const pageRows = filtered.slice(start, end);

    return { filtered: pageRows, total, pageCount, current, all: filtered };
  }, [rows, query, page, pageSize]);

  const goto = (value) => {
    setPage((current) => {
      const target = Math.max(1, Math.min(value, prepared.pageCount));
      return target;
    });
  };

  // Attach "realistic crackle" SVG layers to XX badges/chips
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const reduceMotion =
      typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const map = crackleMapRef.current;
    const ns = "http://www.w3.org/2000/svg";

    function cleanupNode(el) {
      const st = map.get(el);
      if (!st) return;
      st.cancelled = true;
      for (const t of st.timers) clearTimeout(t);
      try {
        if (st.layer && st.layer.parentNode) st.layer.parentNode.removeChild(st.layer);
      } catch {}
      map.delete(el);
    }

    function initNode(el) {
      if (map.has(el)) return;
      const color = (el.getAttribute("data-color") || "#a78bfa").trim();
      const rate = Math.max(0, parseFloat(el.getAttribute("data-rate") || "3"));
      el.style.setProperty("--zap-color", color);
      const layer = document.createElement("span");
      layer.className = "crackle-layer";
      const svg = document.createElementNS(ns, "svg");
      svg.setAttribute("viewBox", "0 0 100 100");
      svg.setAttribute("preserveAspectRatio", "none");
      layer.appendChild(svg);
      el.appendChild(layer);
      if (reduceMotion || rate === 0) {
        map.set(el, { layer, svg, timers: [], cancelled: true, pool: [] });
        return;
      }
      const dpr = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;
      const hairline = 1 / dpr;
      const POOL = 12;
      const pool = [];
      for (let i = 0; i < POOL; i++) {
        const p = document.createElementNS(ns, "path");
        p.setAttribute("class", "spark");
        p.setAttribute("stroke", color);
        const strokeWidth = hairline * (0.9 + Math.random() * 0.2);
        p.setAttribute("stroke-width", strokeWidth.toFixed(3));
        svg.appendChild(p);
        pool.push({ el: p, busy: false });
      }
      const state = { layer, svg, timers: [], cancelled: false, pool, rate };

      function makeSparkPath() {
        // Ring crackle: short jagged arc just outside the chip
        const R = 47;                             // base ring radius (units in viewBox)
        const amp = 1.7 + Math.random() * 2.1;    // radial jitter
        const seg = 5 + ((Math.random() * 3) | 0); // 5–7 segments
        const arc = (8 + Math.random() * 18) * Math.PI / 180; // 8–26° arc span
        const a0  = Math.random() * Math.PI * 2;  // random starting angle

        const pts = [];
        for (let i = 0; i <= seg; i++) {
          const t = i / seg;
          const ang = a0 + (t - 0.5) * arc;
          const ri  = R + (Math.random() * 2 - 1) * amp + (Math.random() < 0.5 ? -0.2 : 0.2);
          pts.push([50 + ri * Math.cos(ang), 50 + ri * Math.sin(ang)]);
        }
        let d = `M${pts[0][0].toFixed(2)} ${pts[0][1].toFixed(2)}`;
        for (let i = 1; i < pts.length; i++) d += `L${pts[i][0].toFixed(2)} ${pts[i][1].toFixed(2)}`;
        // Occasional outward branch
        if (Math.random() < 0.6) {
          const k = 1 + Math.floor(Math.random() * (pts.length - 2));
          const base = pts[k];
          const branchAngle = a0 + ((k / seg) - 0.5) * arc + (Math.random() * 0.6 - 0.3);
          const rb1 = R + amp * (0.6 + Math.random() * 0.8);
          const rb2 = rb1 + Math.random() * amp * 0.9;
          const bx1 = 50 + rb1 * Math.cos(branchAngle);
          const by1 = 50 + rb1 * Math.sin(branchAngle);
          const bx2 = 50 + rb2 * Math.cos(branchAngle + (Math.random() < 0.5 ? 0.8 : -0.8));
          const by2 = 50 + rb2 * Math.sin(branchAngle + (Math.random() < 0.5 ? 0.8 : -0.8));
          d += `M${base[0].toFixed(2)} ${base[1].toFixed(2)} L${bx1.toFixed(2)} ${by1.toFixed(2)} L${bx2.toFixed(2)} ${by2.toFixed(2)}`;
        }
        return d;
      }

      function flashOne() {
        const slot = pool.find((s) => !s.busy);
        if (!slot) return;
        slot.busy = true;
        slot.el.setAttribute("d", makeSparkPath());
        slot.el.classList.add("show");
        const life = 50 + Math.random() * 120;
        const t1 = setTimeout(() => {
          slot.el.classList.remove("show");
          const t2 = setTimeout(() => {
            slot.busy = false;
          }, 110);
          state.timers.push(t2);
        }, life);
        state.timers.push(t1);
      }

      function loop() {
        if (state.cancelled) return;
        const interval = -Math.log(1 - Math.random()) / (state.rate || 1) * 1000;
        const t = setTimeout(() => {
          if (state.cancelled) return;
          const burst = Math.random() < 0.25 ? (2 + (Math.random() < 0.35 ? 1 : 0)) : 1;
          for (let i = 0; i < burst; i++) {
            const ti = setTimeout(() => {
              if (!state.cancelled) flashOne();
            }, i * 22 + Math.random() * 18);
            state.timers.push(ti);
          }
          loop();
        }, interval);
        state.timers.push(t);
      }

      loop();
      map.set(el, state);
    }

    // Attach to current crackle elements
    const targets = Array.from(root.querySelectorAll(".crackle"));
    targets.forEach((el) => initNode(el));
    // Cleanup for removed elements
    for (const el of Array.from(map.keys())) {
      if (!root.contains(el)) cleanupNode(el);
    }

    return () => {
      for (const el of Array.from(map.keys())) cleanupNode(el);
      map.clear();
    };
  }, [rows, query, page, pageSize]);

  const gotoGrade = (gradeValue) => {
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
        if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);
        highlightTimerRef.current = setTimeout(() => setHighlightId(null), 3000);
      }
      setJumpGrade(label);
      const url = new URL(window.location.href);
      url.searchParams.set("grade", label);
      url.searchParams.delete("player");
      url.searchParams.delete("rank");
      window.history.replaceState(null, "", url.toString());
    } catch {}
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

  // Deep-linking via ?player=ID or ?grade=LABEL
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

  const content = useMemo(() => {
    if (loading) {
      return (
        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="min-w-full divide-y divide-slate-800">
            <thead className="bg-slate-900/70 sticky top-0 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">
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
              {prepared.filtered.map((row) => {
                const rank = row.stable_rank ?? "—";
                const shifted = row._shifted;
                const grade = row._grade;
                // Use only the 90d window count for danger logic; do not
                // substitute total tournament counts here.
                const tournamentCount = row.window_tournament_count ?? null;
                const showDanger =
                  tournamentCount === 3 && row.danger_days_left != null;
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
                    className={`hover:bg-slate-900/60 ${
                      isHighlighted ? "ring-2 ring-fuchsia-500/40" : ""
                    }`}
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
                        <span
                          className="text-xs text-slate-500 truncate"
                          title={row.player_id || undefined}
                        >
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
                    <td className="px-4 py-3 whitespace-nowrap" title="Days until this player could fall off the leaderboard">
                      <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${chipClass(severity)}`}>
                        {daysLabel}
                      </span>
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
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-4 space-y-3">
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

          {(() => {
            // Compute visible grades from the current filtered dataset
            const present = new Set(
              prepared.all
                .map((r) => r._grade)
                .filter((g) => g && g !== "—")
            );
            const ordered = DISPLAY_GRADE_SCALE.map(([, label]) => label)
              .slice()
              .reverse() // best first
              .filter((label) => present.has(label));
            if (!ordered.length) return null;
            return (
              <nav className="flex flex-wrap items-center justify-center gap-2">
                {ordered.map((label) => {
                  const active = jumpGrade === label;
      const crackleCls = isXX(label) ? "crackle" : "";
      const dataRate = isXX(label) ? rateFor(label) : undefined;
      return (
        <button
          key={label}
          type="button"
          aria-pressed={active}
          className={`${gradeChipClass(label, active)} ${crackleCls}`}
          data-color={CRACKLE_PURPLE}
          {...(dataRate ? { "data-rate": dataRate } : {})}
          onClick={() => gotoGrade(label)}
        >
                      {label}
                    </button>
                  );
                })}
              </nav>
            );
          })()}

          <form
            className="flex items-center justify-center gap-2"
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
        </div>
      </>
    );
  }, [loading, error, prepared, query, pageSize]);

  return (
    <section ref={rootRef}>
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
