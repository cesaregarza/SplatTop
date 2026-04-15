import { useCallback, useEffect, useState } from "react";
import { fetchJson, isHttpError } from "../http";

const STABLE_ENDPOINT = "/api/ripple/public/leaderboard";
const DANGER_ENDPOINT = "/api/ripple/public/leaderboard/danger";
const META_ENDPOINT = "/api/ripple/public/metadata";
const PERCENTILES_ENDPOINT = "/api/ripple/public/leaderboard/percentiles";

const initialState = {
  loading: true,
  error: null,
  disabled: false,
  stable: null,
  danger: null,
  meta: null,
  percentiles: null,
};

const normalizeError = (err) => {
  if (!err) {
    return "Unknown error";
  }
  if (err.response && err.response.data && err.response.data.detail) {
    return err.response.data.detail;
  }
  return err.message || "Unexpected error";
};

export default function useCompetitionSnapshot() {
  const [state, setState] = useState(initialState);

  const fetchSnapshot = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const [stableRes, dangerRes, metaRes, percentilesRes] = await Promise.all([
        fetchJson(STABLE_ENDPOINT),
        fetchJson(DANGER_ENDPOINT),
        fetchJson(META_ENDPOINT),
        fetchJson(PERCENTILES_ENDPOINT),
      ]);

      setState({
        loading: false,
        error: null,
        disabled: false,
        stable: stableRes,
        danger: dangerRes,
        meta: metaRes,
        percentiles: percentilesRes,
      });
    } catch (err) {
      if (isHttpError(err) && err.response?.status === 404) {
        setState({
          loading: false,
          error: null,
          disabled: true,
          stable: null,
          danger: null,
          meta: null,
          percentiles: null,
        });
        return;
      }

      setState((prev) => ({
        ...prev,
        loading: false,
        error: normalizeError(err),
        percentiles: prev.percentiles,
      }));
    }
  }, []);

  useEffect(() => {
    fetchSnapshot();
  }, [fetchSnapshot]);

  const refresh = useCallback(() => {
    fetchSnapshot();
  }, [fetchSnapshot]);

  return { ...state, refresh };
}
