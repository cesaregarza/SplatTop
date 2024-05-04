import React from "react";

const Aliases = ({ data }) => {
  return (
    <div className="aliases-container mx-auto w-full">
      <h2 className="aliases-title text-2xl font-bold mb-4">Aliases</h2>
      <table className="aliases-table w-full border-collapse">
        <thead>
          <tr className="bg-gray-800 text-white">
            <th className="px-4 py-2 text-right alias-header">Splashtag</th>
            <th className="px-4 py-2 text-left alias-header">Last Seen</th>
          </tr>
        </thead>
        <tbody>
          {data.map(({ splashtag, latest_updated_timestamp }, index) => {
            const splitIndex = splashtag.search(/#\d{4}[0-9a-f]?$/);
            const namePart = splashtag.substring(0, splitIndex);
            const tagPart = splashtag.substring(splitIndex);
            return (
              <tr
                key={`${splashtag}-${index}`}
                className="border-b border-gray-200"
              >
                <td className="px-4 py-2 flex justify-end items-center text-right">
                  <span className="mr-2 text-purplelight">{namePart}</span>
                  <span className="font-medium">{tagPart}</span>
                </td>
                <td className="px-4 py-2 text-left">
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
  );
};

export default Aliases;
