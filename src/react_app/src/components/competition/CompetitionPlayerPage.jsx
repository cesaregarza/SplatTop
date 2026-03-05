import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Link, useParams } from "react-router-dom";
import useCompetitionPlayer from "../../hooks/useCompetitionPlayer";
import useCrackleEffect from "../../hooks/useCrackleEffect";
import {
  CRACKLE_PURPLE,
  DISPLAY_GRADE_SCALE,
  gradeFor,
  isXX,
  nf0,
  nf2,
  tierFor,
} from "./stableLeaderboardUtils";
import CompetitionLayout from "./CompetitionLayout";
import "./StableLeaderboardView.css";
import "./CompetitionPlayerPage.css";

const XX_PLUS_LABEL = "XX+";
const XX_PLUS_THRESHOLD = 250;
const HISTORY_PAGE_SIZE = 12;
const GRADE_INDEX_BY_LABEL = new Map(
  DISPLAY_GRADE_SCALE.map(([, label], index) => [label, index])
);

const formatUtcDateTime = (timestampMs) => {
  if (timestampMs == null) return "—";
  const date = new Date(Number(timestampMs));
  if (Number.isNaN(date.getTime())) return "—";
  return `${date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  })} UTC`;
};

const describeDropStatus = (profile) => {
  const minRequired = Number(profile?.minimum_required_tournaments || 3);
  const rawWindowCount = profile?.window_tournament_count;
  const rawDaysLeft = profile?.danger_days_left;
  const windowCount =
    rawWindowCount == null ? null : Number(rawWindowCount);
  const daysLeft = rawDaysLeft == null ? null : Number(rawDaysLeft);

  if (Number.isFinite(daysLeft)) {
    if (daysLeft < 0) {
      return {
        label: "Inactive",
        className: "bg-rose-500/20 text-rose-100 ring-1 ring-rose-400/25",
      };
    }
    if (daysLeft < 1) {
      return {
        label: "Drops in <1d",
        className: "bg-amber-500/20 text-amber-100 ring-1 ring-amber-400/30",
      };
    }
    return {
      label: `Drops in ${Math.round(daysLeft)}d`,
      className: "bg-amber-500/20 text-amber-100 ring-1 ring-amber-400/30",
    };
  }

  if (Number.isFinite(windowCount) && windowCount >= minRequired) {
    const buffer = windowCount - minRequired;
    return {
      label: `Buffer +${buffer}`,
      className: "bg-emerald-500/20 text-emerald-100 ring-1 ring-emerald-400/25",
    };
  }

  return {
    label: "Not tracking",
    className: "bg-slate-700/30 text-slate-200 ring-1 ring-white/10",
  };
};

const toSafeText = (value) => {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed || null;
};

const toFiniteNumber = (value) => {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
};

const parseRecord = (value) => {
  const raw = toSafeText(value);
  if (!raw) return { wins: null, losses: null };
  const match = /^(\d+)\s*W\s*-\s*(\d+)\s*L$/i.exec(raw);
  if (!match) return { wins: null, losses: null };
  return {
    wins: Number(match[1]),
    losses: Number(match[2]),
  };
};

const normalizeTournamentHistory = (rows) => {
  if (!Array.isArray(rows)) return [];

  const mapped = rows
    .map((row, index) => {
      const tournamentId = row?.tournament_id;
      const tournamentIdLabel =
        tournamentId == null ? null : String(tournamentId);
      const eventMs = toFiniteNumber(row?.event_ms);
      const tournamentName =
        toSafeText(row?.tournament_name) ||
        (tournamentIdLabel ? `Tournament ${tournamentIdLabel}` : "Tournament");
      const placementLabel = toSafeText(row?.placement_label);
      const resultSummary = toSafeText(row?.result_summary);
      const { wins, losses } = parseRecord(resultSummary);
      const matchesPlayed =
        wins != null && losses != null ? wins + losses : null;
      const outcome =
        wins == null || losses == null
          ? "unknown"
          : wins > losses
          ? "positive"
          : wins < losses
          ? "negative"
          : "even";
      const teamName = toSafeText(row?.team_name);
      const teamId =
        row?.team_id == null
          ? null
          : toSafeText(String(row.team_id)) || String(row.team_id);
      const eventDate = eventMs == null ? null : new Date(eventMs);
      const year =
        eventDate && !Number.isNaN(eventDate.getTime())
          ? String(eventDate.getUTCFullYear())
          : null;
      const key = `${tournamentIdLabel || "tournament"}:${eventMs || "na"}:${index}`;

      return {
        key,
        tournamentId: tournamentIdLabel,
        tournamentName,
        eventMs,
        placementLabel,
        resultSummary,
        wins,
        losses,
        matchesPlayed,
        outcome,
        teamName,
        teamId,
        year,
      };
    })
    .filter((row) => row.tournamentId || row.eventMs != null);

  mapped.sort((a, b) => {
    const delta = (b.eventMs ?? -1) - (a.eventMs ?? -1);
    if (delta !== 0) return delta;
    return String(b.tournamentId || "").localeCompare(
      String(a.tournamentId || "")
    );
  });

  return mapped;
};

const buildSnapshotText = ({
  profile,
  grade,
  rankScore,
  minimumRequired,
  lifetimeRanked,
}) => {
  const name = profile?.display_name || "Unknown player";
  const id = profile?.player_id || "unknown";
  const showScore = lifetimeRanked >= minimumRequired;
  const rankLabel =
    showScore && profile?.stable_rank != null
      ? `#${nf0.format(Number(profile.stable_rank))}`
      : "Hidden";
  const scoreLabel =
    showScore && rankScore != null
      ? `${nf2.format(rankScore)} / ${XX_PLUS_THRESHOLD}`
      : "Hidden";
  const tournamentsLabel = `${nf0.format(
    Number(profile?.window_tournament_count || 0)
  )} / ${nf0.format(lifetimeRanked)}`;

  return [
    `${name} (${id})`,
    `Rank: ${rankLabel}`,
    `Grade: ${showScore ? grade : "Hidden"}`,
    `Rank score: ${scoreLabel}`,
    `Tournaments (120d/lifetime): ${tournamentsLabel}`,
    `Last tournament: ${formatUtcDateTime(profile?.last_tournament_ms)}`,
    `Snapshot updated: ${formatUtcDateTime(profile?.generated_at_ms)}`,
  ].join("\n");
};

const copyTextToClipboard = async (text) => {
  if (!text) return false;

  if (
    typeof navigator !== "undefined" &&
    navigator.clipboard?.writeText
  ) {
    await navigator.clipboard.writeText(text);
    return true;
  }

  if (typeof document === "undefined" || !document.body) return false;

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "true");
  textarea.style.position = "absolute";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  document.body.removeChild(textarea);
  return copied;
};

const GradeBadge = ({ label }) => {
  if (!label || label === "—") {
    return (
      <span className="grade-badge grade-tier-default" aria-label="No grade">
        —
      </span>
    );
  }

  const tier = tierFor(label);

  return (
    <span
      className={`grade-badge ${tier}`.trim()}
      title={`Grade ${label}`}
      aria-label={`Grade ${label}`}
    >
      {label}
    </span>
  );
};

const MetricCell = ({
  label,
  value,
  hint,
  className = "",
  hintClassName = "",
}) => (
  <div className={`comp-player-metric-cell ${className}`.trim()}>
    <p className="comp-player-metric-label">{label}</p>
    <p className="comp-player-metric-value">{value}</p>
    {hint ? (
      <p className={`comp-player-metric-hint ${hintClassName}`.trim()}>
        {hint}
      </p>
    ) : null}
  </div>
);

const InsightChip = ({ label, value }) => (
  <div className="comp-player-insight-chip">
    <p className="comp-player-insight-label">{label}</p>
    <p className="comp-player-insight-value font-data">{value}</p>
  </div>
);

const CompetitionPlayerPage = ({ top500Href }) => {
  const { playerId } = useParams();
  const rootRef = useRef(null);
  const [historyQuery, setHistoryQuery] = useState("");
  const [historyYear, setHistoryYear] = useState("all");
  const [historyOutcome, setHistoryOutcome] = useState("all");
  const [historySort, setHistorySort] = useState("recent");
  const [historyPage, setHistoryPage] = useState(1);
  const [shareStatus, setShareStatus] = useState(null);
  const { loading, error, profile, refresh } = useCompetitionPlayer(playerId);

  useEffect(() => {
    const previous = document.title;
    if (!profile) {
      document.title = "Competition - splat.top";
      return () => {
        document.title = previous;
      };
    }
    const displayName = profile.display_name || profile.player_id || "Player";
    document.title = `${displayName} - Competition - splat.top`;
    return () => {
      document.title = previous;
    };
  }, [profile]);

  const minimumRequired = Number(profile?.minimum_required_tournaments || 3);
  const lifetimeRanked = Number(profile?.lifetime_ranked_tournaments || 0);
  const showScore = lifetimeRanked >= minimumRequired;
  const rankScore =
    profile?.display_score == null ? null : Number(profile.display_score) + 150;
  const grade = rankScore == null ? "—" : gradeFor(rankScore);
  const heroHasLightning = Boolean(
    showScore && (grade === "XX+" || grade === "XX★")
  );
  const trackTarget = useMemo(() => {
    if (grade === "XX+" || grade === "XX★") {
      return {
        label: XX_PLUS_LABEL,
        threshold: XX_PLUS_THRESHOLD,
        forceFull: true,
      };
    }
    const gradeIndex = GRADE_INDEX_BY_LABEL.get(grade);
    const currentThresholdEntry =
      gradeIndex != null ? DISPLAY_GRADE_SCALE[gradeIndex] : null;
    const nextThresholdEntry =
      gradeIndex != null && gradeIndex + 1 < DISPLAY_GRADE_SCALE.length
        ? DISPLAY_GRADE_SCALE[gradeIndex + 1]
        : null;
    if (!currentThresholdEntry || !nextThresholdEntry) {
      return {
        label: XX_PLUS_LABEL,
        threshold: XX_PLUS_THRESHOLD,
        forceFull: false,
      };
    }
    const [currentThreshold] = currentThresholdEntry;
    const [, nextLabel] = nextThresholdEntry;
    if (!Number.isFinite(currentThreshold) || nextLabel === "XX★") {
      return {
        label: XX_PLUS_LABEL,
        threshold: XX_PLUS_THRESHOLD,
        forceFull: true,
      };
    }
    return {
      label: nextLabel,
      threshold: Number(currentThreshold),
      forceFull: false,
    };
  }, [grade]);
  const scoreDeltaToThreshold =
    rankScore == null ? null : rankScore - trackTarget.threshold;
  const scoreProgressPct = rankScore == null
    ? 0
    : trackTarget.forceFull
    ? 100
    : Math.max(0, Math.min((rankScore / trackTarget.threshold) * 100, 100));
  const scoreTrackClass =
    rankScore != null && rankScore >= XX_PLUS_THRESHOLD
      ? "comp-player-score-fill is-threshold"
      : "comp-player-score-fill";
  const scoreHasLightning =
    rankScore != null && (rankScore >= XX_PLUS_THRESHOLD || grade === "XX★");
  const scoreHint =
    rankScore == null
      ? "Score hidden until eligible"
      : scoreDeltaToThreshold >= 0
      ? `${nf2.format(scoreDeltaToThreshold)} above ${trackTarget.label} threshold`
      : `${nf2.format(Math.abs(scoreDeltaToThreshold))} below ${trackTarget.label} threshold`;
  const progress = profile?.progress_to_minimum || {
    current: Math.min(lifetimeRanked, minimumRequired),
    required: minimumRequired,
    remaining: Math.max(0, minimumRequired - lifetimeRanked),
  };
  const progressPct = Math.max(
    0,
    Math.min(
      100,
      (Number(progress.current || 0) / Number(progress.required || 1)) * 100
    )
  );
  const dropStatus = useMemo(() => describeDropStatus(profile), [profile]);
  const tournamentHistory = useMemo(
    () => normalizeTournamentHistory(profile?.tournament_history_ranked),
    [profile?.tournament_history_ranked]
  );
  const historyYears = useMemo(
    () =>
      Array.from(
        new Set(tournamentHistory.map((row) => row.year).filter(Boolean))
      ).sort((a, b) => Number(b) - Number(a)),
    [tournamentHistory]
  );
  const filteredHistory = useMemo(() => {
    const query = historyQuery.trim().toLowerCase();
    const filtered = tournamentHistory.filter((row) => {
      if (historyYear !== "all" && row.year !== historyYear) return false;
      if (historyOutcome !== "all" && row.outcome !== historyOutcome) {
        return false;
      }
      if (!query) return true;

      return (
        row.tournamentName?.toLowerCase().includes(query) ||
        row.teamName?.toLowerCase().includes(query) ||
        String(row.tournamentId || "").toLowerCase().includes(query) ||
        String(row.teamId || "").toLowerCase().includes(query)
      );
    });

    filtered.sort((left, right) => {
      if (historySort === "oldest") {
        const delta = (left.eventMs ?? Infinity) - (right.eventMs ?? Infinity);
        if (delta !== 0) return delta;
        return String(left.tournamentId || "").localeCompare(
          String(right.tournamentId || "")
        );
      }
      if (historySort === "most_matches") {
        const delta =
          (right.matchesPlayed ?? -1) - (left.matchesPlayed ?? -1);
        if (delta !== 0) return delta;
      }
      const delta = (right.eventMs ?? -1) - (left.eventMs ?? -1);
      if (delta !== 0) return delta;
      return String(right.tournamentId || "").localeCompare(
        String(left.tournamentId || "")
      );
    });

    return filtered;
  }, [tournamentHistory, historyQuery, historyYear, historyOutcome, historySort]);
  const historyPageCount = Math.max(
    1,
    Math.ceil(filteredHistory.length / HISTORY_PAGE_SIZE)
  );
  const safeHistoryPage = Math.min(historyPage, historyPageCount);
  const historyRows = useMemo(() => {
    const start = (safeHistoryPage - 1) * HISTORY_PAGE_SIZE;
    return filteredHistory.slice(start, start + HISTORY_PAGE_SIZE);
  }, [filteredHistory, safeHistoryPage]);
  const historySummary = useMemo(() => {
    let wins = 0;
    let losses = 0;
    let knownResults = 0;
    let positive = 0;
    for (const row of tournamentHistory) {
      if (row.wins != null && row.losses != null) {
        wins += row.wins;
        losses += row.losses;
        knownResults += 1;
      }
      if (row.outcome === "positive") positive += 1;
    }
    return {
      wins,
      losses,
      knownResults,
      positive,
      uniqueTeams: new Set(
        tournamentHistory
          .map((row) => row.teamId || row.teamName)
          .filter(Boolean)
      ).size,
    };
  }, [tournamentHistory]);
  const historyGeneratedAtMs =
    profile?.history_generated_at_ms ?? profile?.generated_at_ms;
  const historyCount =
    toFiniteNumber(profile?.history_record_count) ?? tournamentHistory.length;
  const shareProfileUrl = useMemo(() => {
    const id = encodeURIComponent(profile?.player_id || playerId || "");
    if (typeof window === "undefined") return `/u/${id}`;
    const origin = window.location.origin.replace(/\/$/, "");
    return `${origin}/u/${id}`;
  }, [playerId, profile?.player_id]);
  const shareSnapshotText = useMemo(
    () =>
      buildSnapshotText({
        profile,
        grade,
        rankScore,
        minimumRequired,
        lifetimeRanked,
      }),
    [profile, grade, rankScore, minimumRequired, lifetimeRanked]
  );

  const handleCopy = useCallback(async (text, successMessage) => {
    try {
      const copied = await copyTextToClipboard(text);
      if (!copied) throw new Error("Clipboard write failed");
      setShareStatus({ kind: "success", message: successMessage });
    } catch {
      setShareStatus({
        kind: "error",
        message: "Clipboard is unavailable in this browser.",
      });
    }
  }, []);

  useCrackleEffect(rootRef, [profile?.player_id, grade, rankScore, showScore]);

  if (loading) {
    return (
      <CompetitionLayout
        generatedAtMs={null}
        stale={false}
        loading={loading}
        onRefresh={refresh}
        faqLinkHref="/"
        faqLinkLabel="View leaderboard"
        vizLinkHref="/learn"
        vizLinkLabel="Interactive explainer"
        top500Href={top500Href}
      >
        <section className="comp-player-empty-card">
          <p>Loading player profile…</p>
        </section>
      </CompetitionLayout>
    );
  }

  if (error) {
    return (
      <CompetitionLayout
        generatedAtMs={null}
        stale={false}
        loading={false}
        onRefresh={refresh}
        faqLinkHref="/"
        faqLinkLabel="View leaderboard"
        vizLinkHref="/learn"
        vizLinkLabel="Interactive explainer"
        top500Href={top500Href}
      >
        <section className="space-y-4">
          <div className="comp-player-error-card">
            <p className="comp-player-error-title">Unable to load player profile</p>
            <p className="comp-player-error-body">{error}</p>
          </div>
          <div className="comp-player-inline-actions">
            <Link
              to="/"
              className="comp-player-button"
            >
              Back to leaderboard
            </Link>
            <button
              type="button"
              onClick={refresh}
              className="comp-player-button"
            >
              Retry
            </button>
          </div>
        </section>
      </CompetitionLayout>
    );
  }

  if (!profile) {
    return (
      <CompetitionLayout
        generatedAtMs={null}
        stale={false}
        loading={false}
        onRefresh={refresh}
        faqLinkHref="/"
        faqLinkLabel="View leaderboard"
        vizLinkHref="/learn"
        vizLinkLabel="Interactive explainer"
        top500Href={top500Href}
      >
        <section className="comp-player-empty-card">
          <p>Player not found.</p>
        </section>
      </CompetitionLayout>
    );
  }

  const movementLabel = !profile.delta_has_baseline
    ? "No baseline snapshot yet"
    : profile.delta_is_new
    ? "New entrant since previous snapshot"
    : Number.isFinite(profile.rank_delta) && profile.rank_delta !== 0
    ? `${profile.rank_delta > 0 ? "+" : ""}${profile.rank_delta} rank`
    : "No rank change";

  const movementScoreLabel = !profile.delta_has_baseline
    ? "—"
    : Number.isFinite(profile.display_score_delta) &&
      Math.abs(profile.display_score_delta) >= 0.01
    ? `${profile.display_score_delta > 0 ? "+" : "-"}${nf2.format(
        Math.abs(profile.display_score_delta)
      )}`
    : "No score change";

  return (
    <CompetitionLayout
      generatedAtMs={profile.generated_at_ms}
      stale={Boolean(profile.stale)}
      loading={loading}
      onRefresh={refresh}
      faqLinkHref="/"
      faqLinkLabel="View leaderboard"
      vizLinkHref="/learn"
      vizLinkLabel="Interactive explainer"
      top500Href={top500Href}
    >
      <section ref={rootRef} className="comp-player-profile">
        <div
          className={`comp-player-hero ${heroHasLightning ? "crackle" : ""}`.trim()}
          data-color={heroHasLightning ? CRACKLE_PURPLE : undefined}
          data-rate={heroHasLightning ? 1.4 : undefined}
        >
          <div className="comp-player-hero-header">
            <div className="comp-player-title-group">
              <p className="comp-player-kicker">Competition profile</p>
              <h2 className="comp-player-name">
                {profile.display_name || "Unknown player"}
              </h2>
              <p className="comp-player-id font-data">{profile.player_id}</p>
            </div>
            <div className="comp-player-actions">
              <Link to="/" className="comp-player-button">
                Back to leaderboard
              </Link>
              <button type="button" onClick={refresh} className="comp-player-button">
                Refresh
              </button>
            </div>
          </div>
          <div className="comp-player-metric-band">
            <MetricCell
              label="Rank"
              value={
                showScore && profile.stable_rank != null
                  ? `#${nf0.format(Number(profile.stable_rank))}`
                  : "—"
              }
              hint={showScore ? movementLabel : "Rank hidden until eligible"}
            />
            <MetricCell
              label="Rank score"
              value={
                showScore && rankScore != null ? (
                <span
                    className={`comp-player-score-value ${scoreHasLightning ? "xxstar-score" : ""}`.trim()}
                  >
                    <span>{nf2.format(rankScore)}</span>
                    <span className="comp-player-score-target"> / {XX_PLUS_THRESHOLD}</span>
                  </span>
                ) : (
                  "—"
                )
              }
              hint={
                showScore
                  ? `${movementScoreLabel} · ${scoreHint}`
                  : "Score hidden until eligible"
              }
              className={scoreHasLightning ? "comp-player-metric-cell--brag" : ""}
              hintClassName={scoreHasLightning ? "text-fuchsia-200/80" : ""}
            />
            <MetricCell
              label="Grade"
              value={showScore ? <GradeBadge label={grade} /> : "—"}
              className={showScore && isXX(grade) ? "comp-player-metric-cell--brag" : ""}
              hintClassName={showScore && isXX(grade) ? "text-fuchsia-200/80" : ""}
              hint={showScore ? (isXX(grade) ? "Top-tier grade unlocked" : null) : null}
            />
            <MetricCell
              label="Drop status"
              value={
                <span className={`comp-player-status-pill ${dropStatus.className}`}>
                  {dropStatus.label}
                </span>
              }
            />
            <MetricCell
              label="Tournaments"
              value={`${nf0.format(
                Number(profile.window_tournament_count || 0)
              )} / ${nf0.format(lifetimeRanked)}`}
              hint="120d / lifetime ranked tournaments"
            />
            <MetricCell
              label="Last tournament"
              value={formatUtcDateTime(profile.last_tournament_ms)}
            />
          </div>
          {showScore && rankScore != null && (
            <div className="comp-player-score-track comp-player-score-track--hero">
              <div className="comp-player-score-track-head">
                <span className="comp-player-track-label">Path to {trackTarget.label}</span>
                <span className="comp-player-track-value font-data">
                  {nf2.format(rankScore)} / {nf2.format(trackTarget.threshold)}
                </span>
              </div>
              <div className="comp-player-score-rail">
                <div className={scoreTrackClass} style={{ width: `${scoreProgressPct}%` }} />
              </div>
            </div>
          )}
        </div>

        {!profile.eligible && (
          <div className="comp-player-note comp-player-note--warn">
            <p className="comp-player-note-title">Player is not currently eligible</p>
            <p className="comp-player-note-body">
              This card uses competition snapshot data only. If this player has
              fewer than {minimumRequired} lifetime ranked tournaments, rank and
              score stay hidden until the minimum is reached.
            </p>
          </div>
        )}

        {!showScore && (
          <div className="comp-player-note">
            <p className="comp-player-note-body">
              Progress to eligibility:{" "}
              <span className="comp-player-note-strong">
                {nf0.format(Number(progress.current || 0))}/
                {nf0.format(Number(progress.required || minimumRequired))}
              </span>{" "}
              ranked tournaments
            </p>
            <div className="comp-player-eligibility-rail">
              <div
                className="comp-player-eligibility-fill"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>
        )}

        <div className="comp-player-main-grid">
          <section className="comp-player-panel comp-player-history-panel">
            <div className="comp-player-panel-head">
              <h3 className="comp-player-panel-title">Ranked history explorer</h3>
              <p className="comp-player-panel-meta">{nf0.format(historyCount)} cached</p>
            </div>
            <p className="comp-player-panel-subtitle">
              Updated {formatUtcDateTime(historyGeneratedAtMs)}
            </p>

            <div className="comp-player-insight-row">
              <InsightChip
                label="Total tournaments"
                value={nf0.format(tournamentHistory.length)}
              />
              <InsightChip
                label="Known match record"
                value={`${nf0.format(historySummary.wins)}W-${nf0.format(historySummary.losses)}L`}
              />
              <InsightChip
                label="Positive events"
                value={nf0.format(historySummary.positive)}
              />
              <InsightChip
                label="Teams played"
                value={nf0.format(historySummary.uniqueTeams)}
              />
            </div>

            <div className="comp-player-controls-strip">
              <input
                type="search"
                value={historyQuery}
                onChange={(event) => {
                  setHistoryQuery(event.target.value);
                  setHistoryPage(1);
                }}
                placeholder="Search tournaments or teams"
                className="comp-player-control"
              />
              <select
                value={historyYear}
                onChange={(event) => {
                  setHistoryYear(event.target.value);
                  setHistoryPage(1);
                }}
                className="comp-player-control"
              >
                <option value="all">All years</option>
                {historyYears.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
              <select
                value={historyOutcome}
                onChange={(event) => {
                  setHistoryOutcome(event.target.value);
                  setHistoryPage(1);
                }}
                className="comp-player-control"
              >
                <option value="all">All outcomes</option>
                <option value="positive">Positive results</option>
                <option value="even">Even results</option>
                <option value="negative">Negative results</option>
                <option value="unknown">Unknown results</option>
              </select>
              <select
                value={historySort}
                onChange={(event) => {
                  setHistorySort(event.target.value);
                  setHistoryPage(1);
                }}
                className="comp-player-control"
              >
                <option value="recent">Newest first</option>
                <option value="oldest">Oldest first</option>
                <option value="most_matches">Most matches</option>
              </select>
            </div>

            {historyRows.length ? (
              <>
                <div className="comp-player-table-wrap">
                  <div className="comp-player-table-scroll">
                    <table className="comp-player-table">
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Tournament</th>
                          <th>Team</th>
                          <th>Result</th>
                        </tr>
                      </thead>
                      <tbody>
                        {historyRows.map((row) => (
                          <tr key={row.key}>
                            <td className="font-data comp-player-table-date">
                              {formatUtcDateTime(row.eventMs)}
                            </td>
                            <td>
                              <p className="comp-player-table-primary">
                                {row.tournamentName}
                              </p>
                              {row.tournamentId && (
                                <p className="comp-player-table-secondary">
                                  Tournament {row.tournamentId}
                                </p>
                              )}
                            </td>
                            <td>
                              <p className="comp-player-table-primary">
                                {row.teamName || "Unknown team"}
                              </p>
                              {row.teamId && (
                                <p className="comp-player-table-secondary">Team {row.teamId}</p>
                              )}
                            </td>
                            <td>
                              <p className="font-data comp-player-table-primary">
                                {row.resultSummary || row.placementLabel || "—"}
                              </p>
                              {row.matchesPlayed != null && (
                                <p className="comp-player-table-secondary">
                                  {nf0.format(row.matchesPlayed)} matches
                                </p>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
                <div className="comp-player-pagination">
                  <p className="comp-player-panel-subtitle">
                    Showing page {nf0.format(safeHistoryPage)} of {nf0.format(historyPageCount)}
                  </p>
                  <div className="comp-player-inline-actions">
                    <button
                      type="button"
                      onClick={() =>
                        setHistoryPage((current) => Math.max(1, current - 1))
                      }
                      disabled={safeHistoryPage <= 1}
                      className="comp-player-button comp-player-button--small"
                    >
                      Prev
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        setHistoryPage((current) =>
                          Math.min(historyPageCount, current + 1)
                        )
                      }
                      disabled={safeHistoryPage >= historyPageCount}
                      className="comp-player-button comp-player-button--small"
                    >
                      Next
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <p className="comp-player-empty-text">No history rows match these filters yet.</p>
            )}
          </section>

          <aside className="comp-player-side-rail">
            <section className="comp-player-panel comp-player-share-panel">
              <h3 className="comp-player-panel-title">Share profile</h3>
              <p className="comp-player-panel-subtitle">
                Copy a direct link or snapshot text for Discord, socials, and team chats.
              </p>
              <div className="comp-player-share-actions">
                <button
                  type="button"
                  onClick={() => handleCopy(shareProfileUrl, "Profile link copied.")}
                  className="comp-player-button comp-player-button--small"
                >
                  Copy profile link
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleCopy(shareSnapshotText, "Profile snapshot text copied.")
                  }
                  className="comp-player-button comp-player-button--small"
                >
                  Copy profile snapshot
                </button>
              </div>
              <p className="comp-player-link-preview">{shareProfileUrl}</p>
              {shareStatus && (
                <p
                  className={`comp-player-share-status ${
                    shareStatus.kind === "error"
                      ? "comp-player-share-status--error"
                      : "comp-player-share-status--ok"
                  }`}
                >
                  {shareStatus.message}
                </p>
              )}
            </section>

            {historySummary.knownResults === 0 && (
              <p className="comp-player-note-tip">
                Match-level results are missing for some tournaments, so those rows
                show unknown outcomes.
              </p>
            )}
          </aside>
        </div>
      </section>
    </CompetitionLayout>
  );
};

export default CompetitionPlayerPage;
