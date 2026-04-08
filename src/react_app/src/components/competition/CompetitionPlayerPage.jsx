import React, {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Link,
  useLoaderData,
  useNavigation,
  useParams,
  useRevalidator,
} from "react-router-dom";
import useCrackleEffect from "../../hooks/useCrackleEffect";
import {
  CRACKLE_PURPLE,
  gradeFor,
  nf0,
  nf2,
} from "./stableLeaderboardUtils";
import CompetitionLayout from "./CompetitionLayout";
import { useCompetitionAuth } from "./CompetitionAuth";
import {
  AtGlanceItem,
  CompetitionPlayerHistoryTable,
  GradeBadge,
  HeaderMetric,
  MatchImpactTable,
  RecentEventRow,
} from "./CompetitionPlayerPageSections";
import { loadCompetitionPlayer } from "./competitionPlayerLoader";
import {
  HISTORY_PAGE_SIZE,
  MATCH_RESULT_VIEW_OPTIONS,
  MATCH_RESULTS_TECHNICAL_NOTE,
  XX_PLUS_THRESHOLD,
  buildHistorySummary,
  describeDropStatus,
  formatRelativeAge,
  formatSignedNumber,
  formatUtcDateTime,
  normalizeMatchLooImpacts,
  normalizeTournamentHistory,
  pickInitialMatchResultView,
  pluralize,
  resolveCompetitionTrackTarget,
  toFiniteNumber,
  toSafeText,
} from "./competitionPlayerPageUtils";
import "./StableLeaderboardView.css";
import "./CompetitionPlayerPage.css";

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

export const CompetitionPlayerPageContent = ({
  error,
  loading,
  playerId,
  profile,
  refresh,
  top500Href,
}) => {
  const rootRef = useRef(null);

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
  const hasLifetimeUnlock = lifetimeRanked >= minimumRequired;
  const rankScore =
    profile?.display_score == null ? null : Number(profile.display_score) + 150;
  const hasVisibleRank = profile?.stable_rank != null;
  const hasVisibleScore = rankScore != null;
  const showsPrivateRankingData =
    !hasLifetimeUnlock && (hasVisibleRank || hasVisibleScore);
  const grade = hasVisibleScore ? gradeFor(rankScore) : "—";
  const heroHasLightning = Boolean(
    hasVisibleScore && (grade === "XX+" || grade === "XX★")
  );
  const trackTarget = useMemo(
    () => resolveCompetitionTrackTarget(grade),
    [grade]
  );
  const scoreDeltaToThreshold =
    rankScore == null ? null : rankScore - trackTarget.threshold;
  const scoreProgressPct =
    rankScore == null
      ? 0
      : trackTarget.forceFull
      ? 100
      : Math.max(0, Math.min((rankScore / trackTarget.threshold) * 100, 100));
  const scoreHasLightning =
    rankScore != null && (rankScore >= XX_PLUS_THRESHOLD || grade === "XX★");
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
  const historyGeneratedAtMs =
    profile?.history_generated_at_ms ?? profile?.generated_at_ms;
  const historyReferenceMs =
    toFiniteNumber(historyGeneratedAtMs) ?? Date.now();
  const historySummary = useMemo(
    () => buildHistorySummary(tournamentHistory, historyReferenceMs),
    [tournamentHistory, historyReferenceMs]
  );
  const matchLooImpacts = useMemo(
    () => normalizeMatchLooImpacts(profile?.match_loo_impacts),
    [profile?.match_loo_impacts]
  );
  const matchImpactHighlightedPlayerNames = useMemo(
    () =>
      Array.from(
        new Set(
          [profile?.display_name, profile?.player_id]
            .map((value) => toSafeText(String(value ?? "")))
            .filter(Boolean)
        )
      ),
    [profile?.display_name, profile?.player_id]
  );
  const matchLooCount =
    toFiniteNumber(profile?.match_loo_record_count) ?? matchLooImpacts.length;
  const harmfulMatchImpacts = useMemo(
    () =>
      matchLooImpacts
        .filter((row) => (row.exactScoreDelta ?? 0) > 0)
        .sort((left, right) => {
          const delta =
            (right.exactScoreDelta ?? -Infinity) -
            (left.exactScoreDelta ?? -Infinity);
          if (delta !== 0) return delta;
          return (right.exactAbsDelta ?? -1) - (left.exactAbsDelta ?? -1);
        }),
    [matchLooImpacts]
  );
  const helpfulMatchImpacts = useMemo(
    () =>
      matchLooImpacts
        .filter((row) => (row.exactScoreDelta ?? 0) < 0)
        .sort((left, right) => {
          const delta =
            (left.exactScoreDelta ?? Infinity) -
            (right.exactScoreDelta ?? Infinity);
          if (delta !== 0) return delta;
          return (right.exactAbsDelta ?? -1) - (left.exactAbsDelta ?? -1);
        }),
    [matchLooImpacts]
  );
  const swingMatchImpacts = matchLooImpacts;
  const hasMatchImpactPanel = matchLooCount > 0 || matchLooImpacts.length > 0;
  const defaultMatchImpactViewId = useMemo(
    () =>
      pickInitialMatchResultView({
        helpfulCount: helpfulMatchImpacts.length,
        harmfulCount: harmfulMatchImpacts.length,
        swingCount: swingMatchImpacts.length,
      }),
    [
      harmfulMatchImpacts.length,
      helpfulMatchImpacts.length,
      swingMatchImpacts.length,
    ]
  );
  const [historyFilters, setHistoryFilters] = useState({
    query: "",
    year: "all",
    outcome: "all",
    sort: "recent",
  });
  const [pageState, setPageState] = useState(() => ({
    history: 1,
    resultsView: defaultMatchImpactViewId,
    dataTab: hasMatchImpactPanel ? "results" : "history",
    expandedImpactRows: {},
  }));
  const [shareStatus, setShareStatus] = useState(null);

  useEffect(() => {
    if (!hasMatchImpactPanel && pageState.dataTab === "results") {
      setPageState((current) => ({
        ...current,
        dataTab: "history",
        resultsView: defaultMatchImpactViewId,
        expandedImpactRows: {},
      }));
    }
  }, [defaultMatchImpactViewId, hasMatchImpactPanel, pageState.dataTab]);

  const filteredHistory = useMemo(() => {
    const query = historyFilters.query.trim().toLowerCase();
    const filtered = tournamentHistory.filter((row) => {
      if (historyFilters.year !== "all" && row.year !== historyFilters.year) {
        return false;
      }
      if (
        historyFilters.outcome !== "all" &&
        row.outcome !== historyFilters.outcome
      ) {
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
      if (historyFilters.sort === "oldest") {
        const delta = (left.eventMs ?? Infinity) - (right.eventMs ?? Infinity);
        if (delta !== 0) return delta;
        return String(left.tournamentId || "").localeCompare(
          String(right.tournamentId || "")
        );
      }
      if (historyFilters.sort === "most_matches") {
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
  }, [tournamentHistory, historyFilters]);
  const showsFullHistoryArchive = profile?.history_max_records === null;
  const historyPageCount = showsFullHistoryArchive
    ? 1
    : Math.max(1, Math.ceil(filteredHistory.length / HISTORY_PAGE_SIZE));
  const safeHistoryPage = showsFullHistoryArchive
    ? 1
    : Math.min(pageState.history, historyPageCount);
  const historyRows = useMemo(() => {
    if (showsFullHistoryArchive) {
      return filteredHistory;
    }
    const start = (safeHistoryPage - 1) * HISTORY_PAGE_SIZE;
    return filteredHistory.slice(start, start + HISTORY_PAGE_SIZE);
  }, [filteredHistory, safeHistoryPage, showsFullHistoryArchive]);
  const strongestHarmfulImpact = harmfulMatchImpacts[0] || null;
  const strongestHelpfulImpact = helpfulMatchImpacts[0] || null;
  const activeMatchImpactView =
    MATCH_RESULT_VIEW_OPTIONS.find(
      (option) =>
        option.id === (pageState.resultsView || defaultMatchImpactViewId)
    ) || MATCH_RESULT_VIEW_OPTIONS[0];
  const activeDataTab =
    pageState.dataTab || (hasMatchImpactPanel ? "results" : "history");
  const activeMatchImpactRows =
    activeMatchImpactView.id === "harmful"
      ? harmfulMatchImpacts
      : activeMatchImpactView.id === "swings"
      ? swingMatchImpacts
      : helpfulMatchImpacts;
  const shareProfileUrl = useMemo(() => {
    const id = encodeURIComponent(profile?.player_id || playerId || "");
    if (typeof window === "undefined") return `/u/${id}`;
    const origin = window.location.origin.replace(/\/$/, "");
    return `${origin}/u/${id}`;
  }, [playerId, profile?.player_id]);

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
  const toggleImpactExpansion = useCallback((rowKey) => {
    setPageState((current) => ({
      ...current,
      expandedImpactRows: {
        ...current.expandedImpactRows,
        [rowKey]: !current.expandedImpactRows[rowKey],
      },
    }));
  }, []);

  useCrackleEffect(rootRef, [
    profile?.player_id,
    grade,
    rankScore,
    hasVisibleScore,
  ]);

  if (loading && !profile && !error) {
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
        loading={loading}
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
            <Link to="/" className="comp-player-button">
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
        loading={loading}
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
    ? "No previous update yet"
    : profile.delta_is_new
    ? "New entrant since previous update"
    : Number.isFinite(profile.rank_delta) && profile.rank_delta !== 0
    ? `${profile.rank_delta > 0 ? "+" : ""}${profile.rank_delta} rank`
    : "No rank change";

  const remainingToUnlock = Math.max(0, minimumRequired - lifetimeRanked);
  const windowCount = Number(profile.window_tournament_count || 0);
  const lastTournamentMs =
    toFiniteNumber(profile.last_tournament_ms) ?? historySummary.latestMs;
  const lastActiveMs =
    toFiniteNumber(profile.last_active_ms) ?? lastTournamentMs;
  const lastSeenLabel = formatRelativeAge(lastTournamentMs, historyReferenceMs);
  const lastActiveLabel = formatRelativeAge(lastActiveMs, historyReferenceMs);
  const recordValue =
    historySummary.knownResults > 0
      ? `${nf0.format(historySummary.wins)}W-${nf0.format(
          historySummary.losses
        )}L`
      : "No logged records";
  const snapshotStatusLabel = profile.eligible
    ? "Live on stable leaderboard"
    : hasLifetimeUnlock
    ? "History unlocked, currently off board"
    : `${pluralize(remainingToUnlock, "event")} to unlock`;
  const winRateValue =
    historySummary.knownWinRate != null
      ? `${nf0.format(historySummary.knownWinRate)}%`
      : "—";
  const averageMatchesValue =
    historySummary.averageMatches == null
      ? "—"
      : nf2.format(historySummary.averageMatches);
  const recentActivityValue =
    historySummary.recent365Count > 0
      ? `${nf0.format(historySummary.recent30Count)} in 30d · ${nf0.format(
          historySummary.recent365Count
        )} in 1y`
      : "No recent archive activity";
  const historySummaryLine = `${nf0.format(
    tournamentHistory.length
  )} tournaments · ${recordValue} · ${nf0.format(
    historySummary.positive
  )} positive · ${nf0.format(historySummary.uniqueTeams)} teams · ${averageMatchesValue} avg matches`;
  const headerScoreDetail =
    rankScore == null
      ? "Score hidden"
      : scoreDeltaToThreshold >= 0
      ? `${nf2.format(scoreDeltaToThreshold)} above ${trackTarget.label}`
      : `${nf2.format(Math.abs(scoreDeltaToThreshold))} to ${trackTarget.label}`;
  const headerRankLabel = hasVisibleRank
    ? `#${nf0.format(Number(profile.stable_rank))}`
    : profile.ineligible_reason === "insufficient_lifetime_tournaments"
    ? "Locked"
    : hasLifetimeUnlock
    ? "Off board"
    : "Locked";
  const resultsHeaderSummary = `Best ${
    strongestHelpfulImpact
      ? formatSignedNumber(
          strongestHelpfulImpact.contributionDelta,
          nf2,
          nf2.format(0)
        )
      : "—"
  } · Worst ${
    strongestHarmfulImpact
      ? formatSignedNumber(
          strongestHarmfulImpact.contributionDelta,
          nf2,
          nf2.format(0)
        )
      : "—"
  } · ${nf0.format(matchLooCount)} shortlisted`;
  const resultsUpdatedMs =
    toFiniteNumber(profile?.match_loo_generated_at_ms) ??
    toFiniteNumber(profile?.generated_at_ms);
  const resultsUpdatedLabel =
    resultsUpdatedMs == null
      ? null
      : `Results updated ${formatRelativeAge(resultsUpdatedMs)}`;
  const visibilityNote =
    profile.ineligible_reason === "insufficient_lifetime_tournaments"
      ? showsPrivateRankingData
        ? `Public profile keeps rank and score locked until ${pluralize(
            remainingToUnlock,
            "more lifetime ranked tournament"
          )}.`
        : `This player needs ${pluralize(
            remainingToUnlock,
            "more lifetime ranked tournament"
          )} before rank and score unlock.`
      : profile.ineligible_reason === "not_currently_eligible"
      ? "This player has enough lifetime history, but they are currently outside the live stable leaderboard snapshot."
      : null;

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
              <div className="comp-player-title-row">
                <h2 className="comp-player-name">
                  {profile.display_name || "Unknown player"}
                </h2>
                <span className="comp-player-title-id font-data">
                  {profile.player_id}
                </span>
                {hasVisibleScore ? (
                  <GradeBadge label={grade} />
                ) : (
                  <span className="comp-player-grade-fallback">
                    {profile.ineligible_reason ===
                    "insufficient_lifetime_tournaments"
                      ? "Locked"
                      : "Off board"}
                  </span>
                )}
                <span className="comp-player-rank-chip font-data">
                  {headerRankLabel}
                </span>
                {hasVisibleRank && movementLabel !== "No rank change" ? (
                  <span className="comp-player-rank-trend">{movementLabel}</span>
                ) : null}
              </div>
            </div>
            <div className="comp-player-hero-controls">
              <div className="comp-player-actions">
                <Link to="/" className="comp-player-back-link">
                  Back
                </Link>
                <button
                  type="button"
                  onClick={() =>
                    handleCopy(shareProfileUrl, "Profile link copied.")
                  }
                  className="comp-player-button comp-player-button--small"
                >
                  Share
                </button>
              </div>
              {shareStatus ? (
                <p
                  className={`comp-player-share-status ${
                    shareStatus.kind === "error"
                      ? "comp-player-share-status--error"
                      : "comp-player-share-status--ok"
                  }`}
                >
                  {shareStatus.message}
                </p>
              ) : null}
            </div>
          </div>

          <div className="comp-player-hero-summary">
            <div className="comp-player-header-metrics">
              <HeaderMetric
                label="Score"
                value={
                  hasVisibleScore ? (
                    <span
                      className={`comp-player-score-value ${
                        scoreHasLightning ? "xxstar-score" : ""
                      }`.trim()}
                    >
                      <span>{nf2.format(rankScore)}</span>
                      <span className="comp-player-score-target">
                        {" "}
                        / {nf0.format(trackTarget.threshold)}
                      </span>
                    </span>
                  ) : (
                    "—"
                  )
                }
                detail={headerScoreDetail}
                tone={scoreHasLightning ? "amber" : "cyan"}
                wide
                progressPct={hasVisibleScore ? scoreProgressPct : null}
                progressLabel={`Path to ${trackTarget.label}`}
                progressClassName={
                  rankScore != null && rankScore >= XX_PLUS_THRESHOLD
                    ? "is-threshold"
                    : ""
                }
              />
              <HeaderMetric
                label="Active"
                value={`${nf0.format(windowCount)}/${nf0.format(
                  minimumRequired
                )}`}
                detail={dropStatus.label}
                tone="emerald"
              />
              <HeaderMetric
                label="Record"
                value={recordValue}
                detail={
                  historySummary.positive > 0
                    ? `${pluralize(historySummary.positive, "positive finish")}`
                    : snapshotStatusLabel
                }
                tone="violet"
              />
              <HeaderMetric
                label="Last active"
                value={lastActiveLabel}
                detail={lastTournamentMs == null ? "No recent timestamp" : `Last tournament ${lastSeenLabel}`}
                tone="rose"
                title={formatUtcDateTime(lastActiveMs)}
              />
            </div>
            <dl className="comp-player-hero-glance">
              <AtGlanceItem label="Win rate" value={winRateValue} />
              <AtGlanceItem label="Recent activity" value={recentActivityValue} />
              <AtGlanceItem
                label="Teams"
                value={nf0.format(historySummary.uniqueTeams)}
              />
              <AtGlanceItem label="Avg matches" value={averageMatchesValue} />
              <AtGlanceItem
                label="Lifetime ranked"
                value={nf0.format(lifetimeRanked)}
              />
            </dl>
          </div>
        </div>

        {!profile.eligible && visibilityNote && (
          <div className="comp-player-note comp-player-note--warn">
            <p className="comp-player-note-title">Player is not currently eligible</p>
            <p className="comp-player-note-body">{visibilityNote}</p>
          </div>
        )}

        {!hasLifetimeUnlock && (
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

        {historySummary.recentEvents.length > 0 ? (
          <section className="comp-player-panel comp-player-recent-panel">
            <div className="comp-player-panel-head">
              <h3 className="comp-player-panel-title">Recent activity</h3>
              <p className="comp-player-panel-meta">
                Last {nf0.format(historySummary.recentEvents.length)}
              </p>
            </div>
            <div className="comp-player-table-wrap">
              <div className="comp-player-table-scroll">
                <table className="comp-player-table comp-player-table--compact">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Tournament</th>
                      <th>Team</th>
                      <th>Result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {historySummary.recentEvents.map((row) => (
                      <RecentEventRow
                        key={row.key}
                        row={row}
                        referenceMs={historyReferenceMs}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        ) : null}

        <section className="comp-player-panel comp-player-data-panel">
          <div className="comp-player-panel-head comp-player-data-head">
            <div
              className="comp-player-data-tabs"
              role="tablist"
              aria-label="Profile data views"
            >
              {hasMatchImpactPanel ? (
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeDataTab === "results"}
                  className={`comp-player-data-tab${
                    activeDataTab === "results" ? " is-active" : ""
                  }`.trim()}
                  onClick={() =>
                    setPageState((current) => ({
                      ...current,
                      dataTab: "results",
                    }))
                  }
                >
                  Strongest results
                </button>
              ) : null}
              <button
                type="button"
                role="tab"
                aria-selected={activeDataTab === "history"}
                className={`comp-player-data-tab${
                  activeDataTab === "history" ? " is-active" : ""
                }`.trim()}
                onClick={() =>
                  setPageState((current) => ({
                    ...current,
                    dataTab: "history",
                  }))
                }
              >
                History explorer
              </button>
            </div>
            <div className="comp-player-data-meta">
              <p className="comp-player-impact-toolbar-summary">
                {activeDataTab === "results"
                  ? resultsHeaderSummary
                  : `${historySummaryLine} · ${nf0.format(
                      filteredHistory.length
                    )} matching`}
              </p>
              {activeDataTab === "results" && resultsUpdatedLabel ? (
                <p
                  className="comp-player-panel-subtitle"
                  title={formatUtcDateTime(resultsUpdatedMs)}
                >
                  {resultsUpdatedLabel}
                </p>
              ) : null}
              {activeDataTab === "results" ? (
                <button
                  type="button"
                  className="comp-player-help-dot"
                  title={MATCH_RESULTS_TECHNICAL_NOTE}
                  aria-label={MATCH_RESULTS_TECHNICAL_NOTE}
                >
                  ?
                </button>
              ) : null}
            </div>
          </div>

          {activeDataTab === "results" && hasMatchImpactPanel ? (
            <div className="comp-player-data-section comp-player-data-section--results">
              {matchLooImpacts.length > 0 ? (
                <>
                  <div className="comp-player-impact-toolbar">
                    <div
                      className="comp-player-impact-view-toggle"
                      role="toolbar"
                      aria-label="Strongest results views"
                    >
                      {MATCH_RESULT_VIEW_OPTIONS.map((option) => {
                        const isActive = activeMatchImpactView.id === option.id;
                        return (
                          <button
                            key={option.id}
                            type="button"
                            aria-pressed={isActive}
                            className={`comp-player-impact-view-button is-${option.tone}${
                              isActive ? " is-active" : ""
                            }`.trim()}
                            onClick={() =>
                              setPageState((current) => ({
                                ...current,
                                resultsView: option.id,
                                expandedImpactRows: {},
                              }))
                            }
                          >
                            {option.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="comp-player-data-body">
                    <MatchImpactTable
                      rows={activeMatchImpactRows}
                      emptyText={activeMatchImpactView.emptyText}
                      referenceMs={historyReferenceMs}
                      highlightedPlayerNames={matchImpactHighlightedPlayerNames}
                      expandedRows={pageState.expandedImpactRows}
                      onToggleExpand={toggleImpactExpansion}
                    />
                  </div>
                </>
              ) : (
                <div className="comp-player-data-body">
                  <p className="comp-player-empty-text">
                    This snapshot does not include shortlisted match-impact rows yet.
                  </p>
                </div>
              )}
            </div>
          ) : null}

          {activeDataTab === "history" ? (
            <div className="comp-player-data-section comp-player-data-section--history">
              <div className="comp-player-controls-strip">
                <input
                  type="search"
                  value={historyFilters.query}
                  onChange={(event) => {
                    setHistoryFilters((current) => ({
                      ...current,
                      query: event.target.value,
                    }));
                    setPageState((current) => ({ ...current, history: 1 }));
                  }}
                  placeholder="Search tournaments or teams"
                  className="comp-player-control"
                />
                <select
                  value={historyFilters.year}
                  onChange={(event) => {
                    setHistoryFilters((current) => ({
                      ...current,
                      year: event.target.value,
                    }));
                    setPageState((current) => ({ ...current, history: 1 }));
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
                  value={historyFilters.outcome}
                  onChange={(event) => {
                    setHistoryFilters((current) => ({
                      ...current,
                      outcome: event.target.value,
                    }));
                    setPageState((current) => ({ ...current, history: 1 }));
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
                  value={historyFilters.sort}
                  onChange={(event) => {
                    setHistoryFilters((current) => ({
                      ...current,
                      sort: event.target.value,
                    }));
                    setPageState((current) => ({ ...current, history: 1 }));
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
                  <CompetitionPlayerHistoryTable
                    rows={historyRows}
                    referenceMs={historyReferenceMs}
                  />
                  {showsFullHistoryArchive ? (
                    <div className="comp-player-data-footer comp-player-pagination">
                      <p className="comp-player-panel-subtitle">
                        Showing all {nf0.format(filteredHistory.length)} matching
                        tournaments
                      </p>
                    </div>
                  ) : (
                    <div className="comp-player-data-footer comp-player-pagination">
                      <p className="comp-player-panel-subtitle">
                        Showing page {nf0.format(safeHistoryPage)} of{" "}
                        {nf0.format(historyPageCount)}
                      </p>
                      <div className="comp-player-inline-actions">
                        <button
                          type="button"
                          onClick={() =>
                            setPageState((current) => ({
                              ...current,
                              history: Math.max(1, current.history - 1),
                            }))
                          }
                          disabled={safeHistoryPage <= 1}
                          className="comp-player-button comp-player-button--small"
                        >
                          Prev
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            setPageState((current) => ({
                              ...current,
                              history: Math.min(
                                historyPageCount,
                                current.history + 1
                              ),
                            }))
                          }
                          disabled={safeHistoryPage >= historyPageCount}
                          className="comp-player-button comp-player-button--small"
                        >
                          Next
                        </button>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="comp-player-data-body">
                  <p className="comp-player-empty-text">
                    No history rows match these filters yet.
                  </p>
                </div>
              )}
            </div>
          ) : null}
        </section>

        {(historySummary.knownResults === 0 ||
          historySummary.placementNotes < tournamentHistory.length) && (
          <p className="comp-player-note-tip">
            Some archived tournaments are missing team names, match records, or
            placement notes, so the profile emphasizes the data that is actually
            present instead of guessing.
          </p>
        )}
      </section>
    </CompetitionLayout>
  );
};

const CompetitionPlayerPage = ({ top500Href }) => {
  const { playerId } = useParams();
  const { accessMode, error, profile } = useLoaderData();
  const navigation = useNavigation();
  const revalidator = useRevalidator();
  const {
    authenticated,
    isAdmin,
    loading: authLoading,
  } = useCompetitionAuth();
  const authResyncRef = useRef(null);
  const playerRouteRef = useRef(null);
  const loading =
    navigation.state !== "idle" || revalidator.state !== "idle";
  const authResyncSignature = `${authenticated ? "auth" : "anon"}:${
    isAdmin ? "admin" : "user"
  }`;

  useLayoutEffect(() => {
    if (!playerId || typeof window === "undefined") return;
    if (typeof window.scrollTo !== "function") return;
    window.scrollTo(0, 0);
  }, [playerId]);

  useEffect(() => {
    if (!playerId || authLoading) return;

    if (playerRouteRef.current !== playerId) {
      playerRouteRef.current = playerId;
      authResyncRef.current = authResyncSignature;
      if (isAdmin && accessMode !== "admin") {
        revalidator.revalidate();
      }
      return;
    }

    if (authResyncRef.current === authResyncSignature) {
      return;
    }

    authResyncRef.current = authResyncSignature;
    revalidator.revalidate();
  }, [
    accessMode,
    authResyncSignature,
    authLoading,
    isAdmin,
    playerId,
    revalidator,
  ]);

  return (
    <CompetitionPlayerPageContent
      key={profile?.player_id || playerId || "missing-player"}
      error={error}
      loading={loading}
      playerId={playerId}
      profile={profile}
      refresh={() => revalidator.revalidate()}
      top500Href={top500Href}
    />
  );
};

export default CompetitionPlayerPage;
export { loadCompetitionPlayer };
