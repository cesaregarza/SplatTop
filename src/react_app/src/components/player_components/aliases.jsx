import React from "react";
import { useTranslation } from "react-i18next";
import {
  sortAliasesByLastSeen,
  splitSplashtag,
} from "./playerPageUtils";

const Aliases = ({ data }) => {
  const { t } = useTranslation("player");
  const aliases = sortAliasesByLastSeen(data);

  return (
    <section className="rounded-lg border border-gray-800/60 bg-gray-950/25 p-4">
      <div className="mb-3 flex items-end justify-between gap-3 border-b border-gray-800/60 pb-3">
        <h2 className="text-lg font-semibold text-white">
          {t("aliases.title")}
        </h2>
        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
          {aliases.length}
        </span>
      </div>
      <div className="max-h-72 overflow-y-auto">
        <table className="w-full border-collapse text-white">
          <thead className="sticky top-0 z-10 border-b border-gray-800 bg-gray-950/95">
            <tr className="text-xs uppercase tracking-[0.12em] text-gray-400">
              <th className="px-4 py-3 text-left">{t("aliases.splashtag")}</th>
              <th className="px-4 py-3 text-left">{t("aliases.last_seen")}</th>
            </tr>
          </thead>
          <tbody>
            {aliases.map(({ splashtag, latest_updated_timestamp }, index) => {
              const { namePart, tagPart } = splitSplashtag(splashtag);

              return (
                <tr
                  key={`${splashtag}-${latest_updated_timestamp || index}`}
                  className={`border-b border-gray-800 ${
                    index === 0 ? "bg-purple-950/20" : "bg-transparent"
                  }`}
                >
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-purplelight">{namePart}</span>
                      {tagPart ? <span>{tagPart}</span> : null}
                      {index === 0 ? (
                        <span className="rounded-full border border-purple-500/50 bg-purple-900/40 px-2 py-0.5 text-xs text-purple-100">
                          {t("aliases.current")}
                        </span>
                      ) : null}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-300">
                    {new Date(latest_updated_timestamp).toLocaleString(
                      "default",
                      {
                        year: "numeric",
                        month: "short",
                        day: "2-digit",
                      }
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default Aliases;
