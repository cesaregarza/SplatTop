import React from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { columnsConfig } from "./columns_config";

const WeaponLeaderboardTable = ({ players }) => {
  const { t } = useTranslation();
  const { t: g } = useTranslation("game");
  const navigate = useNavigate();

  const defaultHeaderClasses = "w-20 px-4 py-2 text-center";
  const defaultCellClasses = "w-20 px-4 py-2 text-center";

  const handleRowClick = (playerId) => {
    navigate(`/player/${playerId}`);
    window.scrollTo(0, 0);
  };
  console.log(players);
  players.sort((a, b) => {
    return b.max_x_power - a.max_x_power;
  });

  players.forEach((player, index) => {
    player.rank = index + 1;
  });

  return (
    <table className="table-auto w-full bg-gray-800">
      <thead>
        <tr className="bg-gray-700">
          {columnsConfig.map((column, index) => (
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
            key={`${player.player_id}_${player.season_number}`}
            className="border-b border-gray-700 hover:bg-purpledark cursor-pointer"
            onClick={() => handleRowClick(player.player_id)}
          >
            {columnsConfig.map((column, index) => (
              <td
                key={index}
                className={column.cellClasses || defaultCellClasses}
              >
                {column.id === "season_number"
                  ? column.render(player, g)
                  : column.render(player, t)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default WeaponLeaderboardTable;
