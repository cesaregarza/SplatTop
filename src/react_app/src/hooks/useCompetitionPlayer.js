import { useCallback, useEffect, useState } from "react";
import axios from "axios";

const normalizeError = (err) => {
  if (!err) return "Unknown error";
  if (err.response?.data?.detail) return err.response.data.detail;
  return err.message || "Unexpected error";
};

const initialState = {
  loading: true,
  error: null,
  profile: null,
};

export default function useCompetitionPlayer(playerId) {
  const [state, setState] = useState(initialState);

  const fetchProfile = useCallback(async () => {
    const id = String(playerId || "").trim();
    if (!id) {
      setState({
        loading: false,
        error: "Missing player id",
        profile: null,
      });
      return;
    }

    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const response = await axios.get(`/api/ripple/public/player/${id}`);
      setState({
        loading: false,
        error: null,
        profile: response.data || null,
      });
    } catch (err) {
      setState({
        loading: false,
        error: normalizeError(err),
        profile: null,
      });
    }
  }, [playerId]);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const refresh = useCallback(() => {
    fetchProfile();
  }, [fetchProfile]);

  return { ...state, refresh };
}
