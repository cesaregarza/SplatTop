import React from "react";

const Aliases = ({ data }) => {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Player Names:</h2>
      <table className="w-full text-left alias-table border border-gray-300">
        <thead>
          <tr className="border-b-4 border-gray-400">
            <th className="px-4 py-2 bg-gray-700">Splashtag</th>
            <th className="px-4 py-2 bg-gray-700">Last Seen</th>
          </tr>
        </thead>
        <tbody>
          {[
            ...new Set(
              data.map(({ splashtag, latest_updated_timestamp }) => ({
                splashtag,
                latest_updated_timestamp,
              }))
            ),
          ].map(({ splashtag, latest_updated_timestamp }, index) => {
            const splitIndex = splashtag.search(/#\d{4}[0-9a-f]?$/);
            const namePart = splashtag.substring(0, splitIndex);
            const tagPart = splashtag.substring(splitIndex);
            return (
              <tr key={`${splashtag}-${index}`} className="border-b border-gray-200">
                <td className="px-4 py-2">
                  <span className="text-purplelight">{namePart}</span>{tagPart}
                </td>
                <td className="px-4 py-2">
                  {new Date(latest_updated_timestamp).toLocaleString("default", {
                    year: "numeric",
                    month: "short",
                    day: "2-digit",
                  })}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default Aliases;
