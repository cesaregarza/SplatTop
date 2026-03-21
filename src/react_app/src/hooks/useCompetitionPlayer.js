import { useCallback, useEffect, useRef, useState } from "react";
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
  const requestSequenceRef = useRef(0);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      requestSequenceRef.current += 1;
    };
  }, []);

  const fetchProfile = useCallback(async () => {
    const id = String(playerId || "").trim();
    const requestSequence = requestSequenceRef.current + 1;
    requestSequenceRef.current = requestSequence;
    if (!id) {
      if (mountedRef.current) {
        setState({
          loading: false,
          error: "Missing player id",
          profile: null,
        });
      }
      return;
    }

    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const response = await axios.get(`/api/ripple/public/player/${id}`);
      if (
        !mountedRef.current ||
        requestSequence !== requestSequenceRef.current
      ) {
        return;
      }
      setState({
        loading: false,
        error: null,
        profile: response.data || null,
      });
    } catch (err) {
      if (
        !mountedRef.current ||
        requestSequence !== requestSequenceRef.current
      ) {
        return;
      }
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
