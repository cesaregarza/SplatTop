import React from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { getColumnsConfig } from "./columns_config";

const WeaponLeaderboardTable = ({ players, isFinal, showWeaponColumn }) => {
  const { t } = useTranslation();
  const { t: g } = useTranslation("game");
  const navigate = useNavigate();
  const columnsConfig = React.useMemo(
    () => getColumnsConfig({ showWeaponColumn }),
    [showWeaponColumn]
  );

  const handleRowClick = (playerId) => {
    navigate(`/player/${playerId}`);
    window.scrollTo(0, 0);
  };

  const keyMap = new Map();

  if (players.length === 0) {
    return (
      <table className="min-w-full table-auto">
        <tbody>
          <tr>
            <td
              className="px-4 py-8 text-center text-lg text-gray-300"
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
    <table className="min-w-full table-auto bg-transparent text-sm">
      <thead>
        <tr className="border-b border-gray-800 bg-gray-950/80">
          {columnsConfig.map((column) => (
            <th key={column.id} className={column.headerClasses}>
              {t(column.title_key)}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {players.map((player) => {
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
              className="border-b border-gray-900/80 hover:bg-purpledark cursor-pointer"
              onClick={() => handleRowClick(player.player_id)}
            >
              {columnsConfig.map((column) => (
                <td key={column.id} className={column.cellClasses}>
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
