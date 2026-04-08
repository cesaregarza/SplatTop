import React from "react";
import { useTranslation } from "react-i18next";

const ThresholdSelector = ({ threshold, setThreshold }) => {
  const { t } = useTranslation("weapon_leaderboard");

  return (
    <div className="flex items-center gap-3">
      <input
        type="range"
        min="0"
        max="1000"
        step="1"
        value={threshold}
        onChange={(event) => setThreshold(parseInt(event.target.value, 10))}
        aria-label={t("threshold_select")}
        className="h-2 flex-1 cursor-pointer appearance-none rounded-full bg-gray-800 accent-purple"
      />
      <div className="min-w-[4.8rem] rounded-md border border-gray-800 bg-gray-950/70 px-2.5 py-1.5 text-right text-sm font-semibold text-white">
        {(threshold / 10).toFixed(1)}%
      </div>
    </div>
  );
};

export default ThresholdSelector;
