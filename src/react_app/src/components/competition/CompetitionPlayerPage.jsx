import React, { useEffect, useMemo, useRef } from "react";
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
  rateFor,
  tierFor,
} from "./stableLeaderboardUtils";
import CompetitionLayout from "./CompetitionLayout";
import "./StableLeaderboardView.css";
import "./CompetitionPlayerPage.css";

const XX_PLUS_LABEL = "XX+";
const XX_PLUS_THRESHOLD = 250;
const GRADE_INDEX_BY_LABEL = new Map(
  DISPLAY_GRADE_SCALE.map(([, label], index) => [label, index])
);
const GRADE_THRESHOLD_BY_LABEL = new Map(
  DISPLAY_GRADE_SCALE.map(([threshold, label]) => [label, threshold])
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

const GradeBadge = ({ label }) => {
  if (!label || label === "—") {
    return (
      <span className="grade-badge grade-tier-default" aria-label="No grade">
        —
      </span>
    );
  }

  const tier = tierFor(label);
  const crackle = isXX(label);
  const dataProps = crackle
    ? { "data-color": CRACKLE_PURPLE, "data-rate": rateFor(label) }
    : {};

  return (
    <span
      className={`grade-badge ${tier} ${crackle ? "crackle" : ""}`.trim()}
      {...dataProps}
      title={`Grade ${label}`}
      aria-label={`Grade ${label}`}
    >
      {label}
    </span>
  );
};

const StatCard = ({ label, value, hint, className = "", hintClassName = "" }) => (
  <div
    className={`comp-player-card rounded-lg border border-slate-800 bg-slate-900/70 p-4 ${className}`.trim()}
  >
    <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
    <p className="mt-2 text-lg font-semibold text-slate-100">{value}</p>
    {hint ? (
      <p className={`mt-1 text-xs text-slate-500 ${hintClassName}`.trim()}>
        {hint}
      </p>
    ) : null}
  </div>
);

const CompetitionPlayerPage = ({ top500Href }) => {
  const { playerId } = useParams();
  const rootRef = useRef(null);
  const { loading, error, profile, refresh } = useCompetitionPlayer(playerId);

  useEffect(() => {
    const previous = document.title;
    if (!profile) {
      document.title = "Competition Player - splat.top";
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
  const heroHasLightning = Boolean(showScore && isXX(grade));
  const trackTarget = useMemo(() => {
    if (grade === "XX+" || grade === "XX★") {
      return {
        label: XX_PLUS_LABEL,
        threshold: XX_PLUS_THRESHOLD,
        forceFull: true,
      };
    }
    const threshold = GRADE_THRESHOLD_BY_LABEL.get(grade);
    const gradeIndex = GRADE_INDEX_BY_LABEL.get(grade);
    const nextLabel =
      gradeIndex != null && gradeIndex + 1 < DISPLAY_GRADE_SCALE.length
        ? DISPLAY_GRADE_SCALE[gradeIndex + 1][1]
        : XX_PLUS_LABEL;
    if (threshold == null || !Number.isFinite(threshold)) {
      return {
        label: XX_PLUS_LABEL,
        threshold: XX_PLUS_THRESHOLD,
        forceFull: false,
      };
    }
    return { label: nextLabel, threshold, forceFull: false };
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
        <section className="rounded-lg border border-slate-800 bg-slate-900/60 p-6">
          <p className="text-slate-300">Loading player profile…</p>
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
          <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-5 text-rose-100">
            <p className="font-semibold">Unable to load player profile</p>
            <p className="mt-1 text-sm">{error}</p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="rounded-md border border-slate-700 bg-slate-900/80 px-4 py-2 text-sm text-slate-100 hover:bg-slate-900"
            >
              Back to leaderboard
            </Link>
            <button
              type="button"
              onClick={refresh}
              className="rounded-md border border-slate-700 bg-slate-900/80 px-4 py-2 text-sm text-slate-100 hover:bg-slate-900"
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
        <section className="rounded-lg border border-slate-800 bg-slate-900/60 p-6">
          <p className="text-slate-300">Player not found.</p>
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
      <section ref={rootRef} className="comp-player-profile space-y-6">
        <div
          className={`comp-player-hero rounded-xl border border-fuchsia-400/20 bg-slate-900/75 p-5 ${heroHasLightning ? "crackle" : ""}`.trim()}
          data-color={heroHasLightning ? CRACKLE_PURPLE : undefined}
          data-rate={heroHasLightning ? 1.4 : undefined}
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-2xl font-semibold text-slate-100 sm:text-3xl">
                {profile.display_name || "Unknown player"}
              </h2>
              <p className="mt-2 font-data text-sm text-slate-400">
                {profile.player_id}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Link
                to="/"
                className="rounded-md border border-slate-700 bg-slate-900/80 px-4 py-2 text-sm text-slate-100 hover:bg-slate-900"
              >
                Back to leaderboard
              </Link>
              <button
                type="button"
                onClick={refresh}
                className="rounded-md border border-slate-700 bg-slate-900/80 px-4 py-2 text-sm text-slate-100 hover:bg-slate-900"
              >
                Refresh
              </button>
            </div>
          </div>
        </div>

      {!profile.eligible && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-amber-100">
          <p className="font-semibold">Player is not currently eligible</p>
          <p className="mt-1 text-sm">
            This card uses competition snapshot data only. If this player has
            fewer than {minimumRequired} lifetime ranked tournaments, rank and
            score stay hidden until the minimum is reached.
          </p>
        </div>
      )}

      {!showScore && (
        <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-300">
            Progress to eligibility:{" "}
            <span className="font-semibold text-slate-100">
              {nf0.format(Number(progress.current || 0))}/
              {nf0.format(Number(progress.required || minimumRequired))}
            </span>{" "}
            ranked tournaments
          </p>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full bg-fuchsia-500/80"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <StatCard
          label="Rank"
          value={
            showScore && profile.stable_rank != null
              ? `#${nf0.format(Number(profile.stable_rank))}`
              : "—"
          }
          hint={showScore ? movementLabel : "Rank hidden until eligible"}
        />
        <StatCard
          label="Rank score"
          value={
            showScore && rankScore != null ? (
              <span
                className={`comp-player-score-value ${scoreHasLightning ? "xxstar-score crackle" : ""}`.trim()}
                data-color={scoreHasLightning ? CRACKLE_PURPLE : undefined}
                data-rate={scoreHasLightning ? 2.8 : undefined}
              >
                <span>{nf2.format(rankScore)}</span>
                <span className="text-sm font-medium text-slate-300/90"> / {XX_PLUS_THRESHOLD}</span>
              </span>
            ) : (
              "—"
            )
          }
          hint={showScore ? `${movementScoreLabel} · ${scoreHint}` : "Score hidden until eligible"}
          className={scoreHasLightning ? "comp-player-card--brag" : ""}
          hintClassName={scoreHasLightning ? "text-fuchsia-200/80" : ""}
        />
        <StatCard
          label="Grade"
          value={showScore ? <GradeBadge label={grade} /> : "—"}
          className={showScore && isXX(grade) ? "comp-player-card--brag crackle" : ""}
          hintClassName={showScore && isXX(grade) ? "text-fuchsia-200/80" : ""}
          hint={
            showScore
              ? isXX(grade)
                ? "Top-tier grade unlocked"
                : null
              : null
          }
        />
        <StatCard
          label="Tournaments"
          value={`${nf0.format(
            Number(profile.window_tournament_count || 0)
          )} / ${nf0.format(lifetimeRanked)}`}
          hint="120d / lifetime ranked tournaments"
        />
        <StatCard
          label="Drop status"
          value={
            <span
              className={`inline-flex rounded-md px-2 py-0.5 text-sm ${dropStatus.className}`}
            >
              {dropStatus.label}
            </span>
          }
        />
        <StatCard
          label="Last tournament"
          value={formatUtcDateTime(profile.last_tournament_ms)}
        />
      </div>
      {showScore && rankScore != null && (
        <div className="comp-player-score-track rounded-lg border border-slate-800 bg-slate-900/70 p-4">
          <div className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-400">
            <span>Path to {trackTarget.label}</span>
            <span className="font-data">{nf2.format(rankScore)} / {nf2.format(trackTarget.threshold)}</span>
          </div>
          <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-slate-800">
            <div
              className={scoreTrackClass}
              style={{ width: `${scoreProgressPct}%` }}
            />
          </div>
        </div>
      )}

      <section className="rounded-lg border border-slate-800 bg-slate-900/70 p-5">
        <h3 className="text-lg font-semibold text-slate-100">
          Tournament history
        </h3>
        <p className="mt-2 text-sm text-slate-400">
          Coming soon. This section will list tournaments entered once the
          compact history payload is added to the nightly snapshot pipeline.
        </p>
      </section>
      </section>
    </CompetitionLayout>
  );
};

export default CompetitionPlayerPage;
