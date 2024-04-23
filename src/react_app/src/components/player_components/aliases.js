import React from "react";

const Aliases = ({ data }) => {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Player Names:</h2>
      <table className="w-full text-left alias-table">
        <thead>
          <tr>
            <th className="px-4 py-2">Splashtag</th>
            <th className="px-4 py-2">Last Seen</th>
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
          ].map(({ splashtag, latest_updated_timestamp }, index) => (
            <tr key={`${splashtag}-${index}`}>
              <td className="px-4 py-2">{splashtag}</td>
              <td className="px-4 py-2">
                {new Date(latest_updated_timestamp).toLocaleString("default", {
                  year: "numeric",
                  month: "short",
                  day: "2-digit",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default Aliases;
