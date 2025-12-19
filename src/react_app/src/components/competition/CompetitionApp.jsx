import React, { useEffect, useMemo } from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import CompetitionLayout from "./CompetitionLayout";
import StableLeaderboardView from "./StableLeaderboardView";
import CompetitionFaq from "./CompetitionFaq";
import CompetitionViz from "./CompetitionViz";
import useCompetitionSnapshot from "../../hooks/useCompetitionSnapshot";

const resolveMainSiteUrl = () => {
  const override = process.env.REACT_APP_MAIN_SITE_URL;
  if (override) return override;

  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    if (hostname === "comp.localhost") {
      return `${protocol}//localhost:3000/`;
    }
  }

  return "https://splat.top/";
};

const MAIN_SITE_URL = resolveMainSiteUrl();

const CompetitionLeaderboardPage = ({ snapshot }) => {
  const { loading, error, disabled, stable, danger, refresh } = snapshot;
  const generatedAtMs = stable?.generated_at_ms ?? danger?.generated_at_ms ?? null;

  useEffect(() => {
    const previous = document.title;
    document.title = "Competitive Leaderboard - splat.top";
    return () => {
      document.title = previous;
    };
  }, []);

  const mergedRows = useMemo(() => {
    const stableRows = Array.isArray(stable?.data) ? stable.data : [];
    const dangerRows = Array.isArray(danger?.data) ? danger.data : [];
    const deltas = stable?.deltas ?? null;
    const dangerById = new Map(dangerRows.map((row) => [row.player_id, row]));
    const deltaPlayers = deltas?.players ?? {};
    const hasBaseline = deltas?.baseline_generated_at_ms != null;
    const newcomerIds = new Set(deltas?.newcomers ?? []);
    const deltaWindowMs = 24 * 60 * 60 * 1000;

    const resolveDisplayDelta = (entry) => {
      if (!entry) return null;
      if (typeof entry.display_score_delta === "number") {
        return entry.display_score_delta;
      }
      if (typeof entry.score_delta === "number") {
        return entry.score_delta * 25;
      }
      return null;
    };

    return stableRows.map((row) => {
      const playerId = row.player_id;
      const dangerRow = dangerById.get(playerId);
      const deltaEntry = playerId != null ? deltaPlayers[playerId] : undefined;
      const rankDelta = hasBaseline && deltaEntry && typeof deltaEntry.rank_delta === "number"
        ? deltaEntry.rank_delta
        : null;
      let displayScoreDelta = hasBaseline ? resolveDisplayDelta(deltaEntry) : null;
      const isNewEntry = hasBaseline && Boolean(deltaEntry?.is_new || newcomerIds.has(playerId));
      const lastTournamentMs = row.last_tournament_ms ?? null;

      if (
        displayScoreDelta != null &&
        generatedAtMs != null &&
        lastTournamentMs != null &&
        generatedAtMs - lastTournamentMs > deltaWindowMs
      ) {
        displayScoreDelta = null;
      }

      return {
        ...row,
        danger_days_left: dangerRow?.days_left ?? null,
        danger_next_expiry_ms: dangerRow?.next_expiry_ms ?? null,
        danger_oldest_in_window_ms: dangerRow?.oldest_in_window_ms ?? null,
        // Prefer danger's live window count; otherwise use stable payload's
        // window count when available. Do NOT fall back to total tournaments,
        // as that incorrectly implies all tournaments occurred in the window.
        window_tournament_count:
          dangerRow?.window_tournament_count ?? row.window_tournament_count ?? null,
        rank_delta: rankDelta,
        display_score_delta: displayScoreDelta,
        delta_is_new: isNewEntry,
        delta_has_baseline: hasBaseline,
        delta_previous_rank:
          deltaEntry && typeof deltaEntry.previous_rank === "number"
            ? deltaEntry.previous_rank
            : null,
        delta_previous_display_score:
          deltaEntry && typeof deltaEntry.previous_display_score === "number"
            ? deltaEntry.previous_display_score
            : null,
      };
    });
  }, [stable?.data, stable?.deltas, danger?.data, generatedAtMs]);

  if (disabled) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center px-6">
        <div className="max-w-lg text-center">
          <h1 className="text-3xl font-semibold">Competitive leaderboard disabled</h1>
          <p className="mt-4 text-slate-400">
            The public competitive leaderboard is currently turned off. Check
            back later or contact an administrator if you believe this is a
            mistake.
          </p>
        </div>
      </div>
    );
  }

  const stale = Boolean(stable?.stale || danger?.stale);
  const windowDays = stable?.query_params?.tournament_window_days ?? null;

  return (
    <CompetitionLayout
      generatedAtMs={generatedAtMs}
      stale={stale}
      loading={loading}
      onRefresh={refresh}
      faqLinkHref="/faq"
      faqLinkLabel="How rankings work"
      vizLinkHref="/learn"
      vizLinkLabel="Interactive explainer"
      top500Href={MAIN_SITE_URL}
    >
      {error && (
        <div className="mb-6 rounded-md border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {error}
        </div>
      )}

      <div className="grid gap-8">
        <StableLeaderboardView
          rows={mergedRows}
          loading={loading}
          error={error}
          windowDays={windowDays}
          onRefresh={refresh}
        />
      </div>
    </CompetitionLayout>
  );
};

const CompetitionFaqPage = ({ snapshot }) => {
  const { loading, stable, danger, disabled, percentiles } = snapshot;

  useEffect(() => {
    const previous = document.title;
    document.title = "Competitive Leaderboard FAQ - splat.top";
    return () => {
      document.title = previous;
    };
  }, []);

  const generatedAtMs = stable?.generated_at_ms ?? danger?.generated_at_ms;
  const stale = Boolean(stable?.stale || danger?.stale);

  return (
    <CompetitionLayout
      generatedAtMs={generatedAtMs}
      stale={stale}
      loading={loading}
      faqLinkHref="/"
      faqLinkLabel="View leaderboard"
      vizLinkHref="/learn"
      vizLinkLabel="Interactive explainer"
      top500Href={MAIN_SITE_URL}
    >
      {disabled && (
        <div className="mb-6 rounded-md border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          The public competitive leaderboard is currently turned off, but you can
          still review how the system works below.
        </div>
      )}
      <CompetitionFaq percentiles={percentiles} />
    </CompetitionLayout>
  );
};

const CompetitionRoutes = () => {
  const snapshot = useCompetitionSnapshot();

  return (
    <Routes>
      <Route path="/learn" element={<CompetitionViz />} />
      <Route path="/viz" element={<CompetitionViz />} />
      <Route path="/faq" element={<CompetitionFaqPage snapshot={snapshot} />} />
      <Route path="*" element={<CompetitionLeaderboardPage snapshot={snapshot} />} />
    </Routes>
  );
};

const CompetitionApp = () => (
  <Router>
    <CompetitionRoutes />
  </Router>
);

export default CompetitionApp;
