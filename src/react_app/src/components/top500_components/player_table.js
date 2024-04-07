import React from "react";

import columnsConfig from "./columns_config";

const PlayerTable = ({ players, columnVisibility }) => {
  const visibleColumns = columnsConfig.filter(
    (column) => columnVisibility[column.id]
  );

  const defaultHeaderClasses = "w-20 px-4 py-2 text-center";
  const defaultCellClasses = "w-20 px-4 py-2 text-center";

  return (
    <table className="table-auto w-full bg-gray-800">
      <thead>
        <tr className="bg-gray-700">
          {visibleColumns.map((column, index) => (
            <th
              key={index}
              className={column.headerClasses || defaultHeaderClasses}
            >
              {column.name}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {players.map((player) => (
          <tr
            key={player.player_id}
            className="border-b border-gray-700 hover:bg-purpledark"
          >
            {visibleColumns.map((column, index) => (
              <td
                key={index}
                className={column.cellClasses || defaultCellClasses}
              >
                {column.render(player)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default PlayerTable;
