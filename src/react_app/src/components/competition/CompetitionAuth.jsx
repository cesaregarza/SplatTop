import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  fetchCompetitionAuthState,
  logoutCompetitionAuth,
  writeCachedCompetitionAuthState,
} from "./competitionAuthApi";

const defaultCompetitionAuthState = {
  available: true,
  authenticated: false,
  isAdmin: false,
  discordId: null,
  error: null,
  loading: false,
  logoutPending: false,
  logout: async () => ({
    authenticated: false,
    isAdmin: false,
    discordId: null,
  }),
  refresh: async () => ({
    authenticated: false,
    isAdmin: false,
    discordId: null,
  }),
};

const CompetitionAuthContext = createContext(defaultCompetitionAuthState);

const normalizeCompetitionAuthError = (error) => {
  if (!error) return "Unable to load Discord auth";
  if (typeof error.message === "string" && error.message.trim()) {
    return error.message;
  }
  return "Unable to load Discord auth";
};

export const CompetitionAuthProvider = ({ children }) => {
  const [authState, setAuthState] = useState({
    available: true,
    authenticated: false,
    isAdmin: false,
    discordId: null,
    error: null,
    loading: true,
    logoutPending: false,
  });

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    const loadAuthState = async () => {
      try {
        const nextState = await fetchCompetitionAuthState(controller.signal);
        if (!active) return;

        setAuthState((current) => ({
          ...current,
          ...nextState,
          error: null,
          loading: false,
          logoutPending: false,
        }));
      } catch (error) {
        if (error?.name === "AbortError" || !active) {
          return;
        }

        writeCachedCompetitionAuthState({
          available: defaultCompetitionAuthState.available,
          authenticated: false,
          isAdmin: false,
          discordId: null,
        });
        setAuthState((current) => ({
          ...current,
          authenticated: false,
          isAdmin: false,
          available: current.available,
          discordId: null,
          error: normalizeCompetitionAuthError(error),
          loading: false,
          logoutPending: false,
        }));
      }
    };

    loadAuthState();

    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  const contextValue = useMemo(() => {
    const refresh = async () => {
      setAuthState((current) => ({
        ...current,
        loading: true,
        error: null,
      }));

      try {
        const nextState = await fetchCompetitionAuthState();
        setAuthState((current) => ({
          ...current,
          ...nextState,
          error: null,
          loading: false,
          logoutPending: false,
        }));
        return nextState;
      } catch (error) {
        writeCachedCompetitionAuthState({
          available: authState.available,
          authenticated: false,
          isAdmin: false,
          discordId: null,
        });
        setAuthState((current) => ({
          ...current,
          authenticated: false,
          isAdmin: false,
          available: current.available,
          discordId: null,
          error: normalizeCompetitionAuthError(error),
          loading: false,
          logoutPending: false,
        }));
        throw error;
      }
    };

    const logout = async () => {
      setAuthState((current) => ({
        ...current,
        error: null,
        logoutPending: true,
      }));

      try {
        const nextState = await logoutCompetitionAuth();
        setAuthState({
          ...nextState,
          error: null,
          loading: false,
          logoutPending: false,
        });
        return nextState;
      } catch (error) {
        writeCachedCompetitionAuthState({
          available: authState.available,
          authenticated: false,
          isAdmin: false,
          discordId: null,
        });
        setAuthState((current) => ({
          ...current,
          error: normalizeCompetitionAuthError(error),
          logoutPending: false,
        }));
        throw error;
      }
    };

    return {
      ...authState,
      logout,
      refresh,
    };
  }, [authState]);

  return (
    <CompetitionAuthContext.Provider value={contextValue}>
      {children}
    </CompetitionAuthContext.Provider>
  );
};

export const useCompetitionAuth = () => useContext(CompetitionAuthContext);
