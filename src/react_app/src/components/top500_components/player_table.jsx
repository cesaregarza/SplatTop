import React from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { columnsConfig } from "./columns_config";

const PlayerTable = ({ players, columnVisibility, tableContext = {} }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const visibleColumns = columnsConfig.filter(
    (column) => columnVisibility[column.id]
  );

  const defaultHeaderClasses =
    "w-20 px-4 py-3 text-center text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-gray-300";
  const defaultCellClasses = "w-20 px-4 py-3 text-center align-middle";

  const handleRowClick = (playerId) => {
    navigate(`/player/${playerId}`);
    window.scrollTo(0, 0);
  };

  return (
    <table className="w-full table-auto border-collapse bg-transparent">
      <thead>
        <tr className="border-b border-gray-800 bg-gray-950/95">
          {visibleColumns.map((column, index) => (
            <th
              key={index}
              className={column.headerClasses || defaultHeaderClasses}
            >
              {t(column.title_key)}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {players.map((player) => (
          <tr
            key={player.player_id}
            className="cursor-pointer border-b border-gray-800/90 hover:bg-purple-950/30"
            onClick={() => handleRowClick(player.player_id)}
          >
            {visibleColumns.map((column, index) => (
              <td
                key={index}
                className={column.cellClasses || defaultCellClasses}
              >
                {column.render(player, t, tableContext)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default PlayerTable;
