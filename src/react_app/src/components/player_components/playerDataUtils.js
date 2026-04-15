const aggregatedKeys = [
  "weapon_counts",
  "weapon_winrate",
  "season_results",
  "aggregate_season_data",
  "latest_data",
];

const createPlayerDetailStreamState = () => ({
  chartData: null,
  analysisReady: false,
  analysisLoading: false,
  analysisError: null,
});

const createEmptyPlayerDetailData = () => ({
  player_data: [],
  aggregated_data: aggregatedKeys.reduce(
    (accumulator, key) => ({ ...accumulator, [key]: [] }),
    {}
  ),
});

const mergePlayerDetailPayload = (currentData, payload) => {
  const nextData = {
    ...createEmptyPlayerDetailData(),
    ...(currentData || {}),
    aggregated_data: {
      ...createEmptyPlayerDetailData().aggregated_data,
      ...(currentData?.aggregated_data || {}),
    },
  };

  if (!payload || typeof payload !== "object") {
    return nextData;
  }

  if (Array.isArray(payload.player_data)) {
    nextData.player_data = payload.player_data;
  }

  const aggregatedPayload = payload.aggregated_data || {};
  aggregatedKeys.forEach((key) => {
    if (Array.isArray(aggregatedPayload[key])) {
      nextData.aggregated_data[key] = aggregatedPayload[key];
    }
  });

  return nextData;
};

const isPlayerChunkEnvelope = (payload) =>
  Boolean(
    payload &&
      typeof payload === "object" &&
      payload.type === "player_chunk" &&
      payload.version === 2 &&
      typeof payload.phase === "string"
  );

const isLegacyPlayerDetailPayload = (payload) =>
  Boolean(
    payload &&
      typeof payload === "object" &&
      payload.type !== "player_chunk" &&
      (Array.isArray(payload.player_data) || payload.aggregated_data)
  );

const reducePlayerDetailStreamState = (currentState, payload) => {
  const nextState = {
    ...createPlayerDetailStreamState(),
    ...(currentState || {}),
  };
  const currentChartData =
    nextState.chartData || createEmptyPlayerDetailData();

  if (isPlayerChunkEnvelope(payload)) {
    const phase = payload.phase;
    const chunkPayload = payload.payload || {};

    if (phase === "snapshot") {
      return {
        chartData: mergePlayerDetailPayload(currentChartData, chunkPayload),
        analysisReady: false,
        analysisLoading: true,
        analysisError: null,
      };
    }

    if (phase === "analysis") {
      return {
        chartData: mergePlayerDetailPayload(currentChartData, chunkPayload),
        analysisReady: true,
        analysisLoading: false,
        analysisError: null,
      };
    }

    if (phase === "error") {
      return {
        ...nextState,
        analysisLoading: false,
        analysisError:
          chunkPayload.message || "Unable to load player analysis data.",
      };
    }

    if (phase === "complete") {
      return {
        ...nextState,
        analysisLoading: false,
      };
    }

    return nextState;
  }

  if (isLegacyPlayerDetailPayload(payload)) {
    return {
      chartData: mergePlayerDetailPayload(currentChartData, payload),
      analysisReady: true,
      analysisLoading: false,
      analysisError: null,
    };
  }

  return nextState;
};

export {
  createPlayerDetailStreamState,
  createEmptyPlayerDetailData,
  isLegacyPlayerDetailPayload,
  isPlayerChunkEnvelope,
  mergePlayerDetailPayload,
  reducePlayerDetailStreamState,
};
