import React, { useEffect, useMemo } from "react";
import {
  Outlet,
  Route,
  RouterProvider,
  createBrowserRouter,
  createRoutesFromElements,
  useLoaderData,
  useOutletContext,
  useRevalidator,
} from "react-router-dom";
import CompetitionLayout from "./CompetitionLayout";
import StableLeaderboardView from "./StableLeaderboardView";
import CompetitionFaq from "./CompetitionFaq";
import CompetitionViz from "./CompetitionViz";
import CompetitionErrorBoundary from "./CompetitionErrorBoundary";
import { CompetitionAuthProvider } from "./CompetitionAuth";
import { resolveCompetitionMainSiteUrl } from "./competitionHost";
import { loadCompetitionSnapshot } from "./competitionSnapshotApi";
import { mergeCompetitionSnapshotRows } from "./competitionSnapshotUtils";
import CompetitionPlayerPage, {
  primeCompetitionPlayerRoute,
} from "./CompetitionPlayerPage";

const MAIN_SITE_URL = resolveCompetitionMainSiteUrl();

export const CompetitionRouteShell = () => {
  const snapshotData = useLoaderData();
  const revalidator = useRevalidator();
  const snapshot = {
    ...snapshotData,
    loading: revalidator.state === "loading",
    refresh: () => revalidator.revalidate(),
  };
  return <Outlet context={{ snapshot }} />;
};

const useCompetitionRouteContext = () => useOutletContext();

export const CompetitionLeaderboardPage = () => {
  const { snapshot } = useCompetitionRouteContext();
  const { loading, error, disabled, stable, danger, refresh } = snapshot;
  const generatedAtMs = stable?.generated_at_ms ?? danger?.generated_at_ms ?? null;

  useEffect(() => {
    const previous = document.title;
    document.title = "Competitive Leaderboard - splat.top";
    return () => {
      document.title = previous;
    };
  }, []);

  const mergedRows = useMemo(
    () => mergeCompetitionSnapshotRows({ stable, danger }),
    [stable, danger]
  );

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

export const CompetitionFaqPage = () => {
  const { snapshot } = useCompetitionRouteContext();
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

export const createCompetitionRouter = () => createBrowserRouter(
  createRoutesFromElements(
    <Route>
      <Route
        path="/learn"
        element={(
          <CompetitionErrorBoundary>
            <CompetitionViz />
          </CompetitionErrorBoundary>
        )}
      />
      <Route
        path="/viz"
        element={(
          <CompetitionErrorBoundary>
            <CompetitionViz />
          </CompetitionErrorBoundary>
        )}
      />
      <Route
        path="/u/:playerId"
        loader={primeCompetitionPlayerRoute}
        element={<CompetitionPlayerPage top500Href={MAIN_SITE_URL} />}
      />
      <Route
        loader={loadCompetitionSnapshot}
        element={<CompetitionRouteShell />}
      >
        <Route path="/faq" element={<CompetitionFaqPage />} />
        <Route path="*" element={<CompetitionLeaderboardPage />} />
      </Route>
    </Route>
  )
);

const CompetitionApp = () => {
  const router = useMemo(() => createCompetitionRouter(), []);
  return (
    <CompetitionAuthProvider>
      <RouterProvider router={router} />
    </CompetitionAuthProvider>
  );
};

export default CompetitionApp;
export { loadCompetitionSnapshot };
