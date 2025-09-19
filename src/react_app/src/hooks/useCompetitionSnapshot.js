import { useCallback, useEffect, useState } from "react";
import axios from "axios";

const STABLE_ENDPOINT = "/api/ripple/public";
const DANGER_ENDPOINT = "/api/ripple/public/danger";
const META_ENDPOINT = "/api/ripple/public/meta";

const initialState = {
  loading: true,
  error: null,
  disabled: false,
  stable: null,
  danger: null,
  meta: null,
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
      const [stableRes, dangerRes, metaRes] = await Promise.all([
        axios.get(STABLE_ENDPOINT),
        axios.get(DANGER_ENDPOINT),
        axios.get(META_ENDPOINT),
      ]);

      setState({
        loading: false,
        error: null,
        disabled: false,
        stable: stableRes.data,
        danger: dangerRes.data,
        meta: metaRes.data,
      });
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 404) {
        setState({
          loading: false,
          error: null,
          disabled: true,
          stable: null,
          danger: null,
          meta: null,
        });
        return;
      }

      setState((prev) => ({
        ...prev,
        loading: false,
        error: normalizeError(err),
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
