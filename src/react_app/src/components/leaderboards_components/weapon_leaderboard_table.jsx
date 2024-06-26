import React from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { columnsConfig } from "./columns_config";

const WeaponLeaderboardTable = ({ players, isFinal }) => {
  const { t } = useTranslation();
  const { t: g } = useTranslation("game");
  const navigate = useNavigate();

  const defaultHeaderClasses = "w-20 px-4 py-2 text-center";
  const defaultCellClasses = "w-20 px-4 py-2 text-center";

  const handleRowClick = (playerId) => {
    navigate(`/player/${playerId}`);
    window.scrollTo(0, 0);
  };

  const keyMap = new Map();

  if (players.length === 0) {
    return (
      <table className="table-auto w-full bg-gray-800">
        <tbody>
          <tr>
            <td
              className="px-4 py-2 text-center text-lg"
              colSpan={columnsConfig.length}
            >
              No results
            </td>
          </tr>
        </tbody>
      </table>
    );
  }

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
        {players.map((player, playerIndex) => {
          const key = `${player.player_id}_${player.season_number}_${
            player.weapon_id
          }_${isFinal ? "final" : "peak"}`;

          if (keyMap.has(key)) {
            console.warn(`Duplicate key found: ${key}`);
          } else {
            keyMap.set(key, player);
          }

          return (
            <tr
              key={key}
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
          );
        })}
      </tbody>
    </table>
  );
};

export default WeaponLeaderboardTable;
