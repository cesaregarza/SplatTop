import React from "react";

const Aliases = ({ data }) => {
  return (
    <div className="aliases-container mx-auto w-full mt-5">
      <h2 className="aliases-title text-2xl font-bold mb-4">Aliases</h2>
      <div className="relative overflow-y-auto max-h-48">
        <table className="aliases-table w-full border-collapse">
          <thead className="sticky bg-gray-800 text-white z-10 border-b-2 border-gray-800 aliases-header">
            <tr>
              <th className="px-4 py-2 text-right">Splashtag</th>
              <th className="px-4 py-2 text-left">Last Seen</th>
            </tr>
          </thead>
          <tbody>
            {data.map(
              ({ splashtag, latest_updated_timestamp }, index) => {
                const splitIndex = splashtag.search(/#\d{4}[0-9a-f]?$/);
                const namePart = splashtag.substring(0, splitIndex);
                const tagPart = splashtag.substring(splitIndex);
                return (
                  <tr
                    key={`${splashtag}-${index}`}
                    className="border-b border-gray-200"
                  >
                    <td className="px-4 py-2 flex justify-end items-center">
                      <span className="mr-2 text-purplelight">{namePart}</span>
                      <span>{tagPart}</span>
                    </td>
                    <td className="px-4 py-2">
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
              }
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Aliases;
