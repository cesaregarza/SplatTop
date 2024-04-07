import React from "react";

import * as RankColumn from "./columns/rank_column";
import * as WeaponColumn from "./columns/weapon_column";
import * as SplashtagColumn from "./columns/splashtag_column";
import * as BadgesColumn from "./columns/badges_column";
import * as XPowerColumn from "./columns/xpower_column";

const PlayerTable = ({ players }) => {
  const columns = [
    RankColumn,
    WeaponColumn,
    SplashtagColumn,
    BadgesColumn,
    XPowerColumn,
  ];

  const defaultHeaderClasses = "w-20 px-4 py-2 text-center";
  const defaultCellClasses = "w-20 px-4 py-2 text-center";

  return (
    <table className="table-auto w-full bg-gray-800">
      <thead>
        <tr className="bg-gray-700">
          {columns.map((column, index) => (
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
            {columns.map((column, index) => (
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
