import React from "react";
import DiamondBadge from "./badges/diamond_badge";
import Top10Badge from "./badges/top10_badge";
import Top500Badge from "./badges/top500_badge";
import TentatekIcon from "../../assets/icons/tentatek.png";
import TakorokaIcon from "../../assets/icons/takoroka.png";

const PlayerTable = ({ players }) => {
  return (
    <table className="table-auto w-full bg-gray-800">
      <thead>
        <tr className="bg-gray-700">
          <th className="w-20 px-4 py-2 text-center">Rank</th>
          <th className="w-20 px-4 py-2 text-center">Weapon</th>
          <th className="flex-grow px-4 py-2 text-center">Splashtag</th>
          <th className="flex-grow px-4 py-2 text-center">Data</th>
          <th className="w-20 px-4 py-2 text-right">X Power</th>
        </tr>
      </thead>
      <tbody>
        {players.map((player) => (
          <tr
            key={player.player_id}
            className="border-b border-gray-700 hover:bg-purpledark"
          >
            <td className="w-20 px-4 py-2 text-center">{player.rank}</td>
            <td className="w-20 px-4 py-2 text-center">
              <div className="bg-black rounded-full flex justify-center items-center h-10 w-10 mx-auto">
                <img
                  src={player.weapon_image}
                  alt="Weapon name not yet supported"
                  className="h-10 w-10 object-cover aspect-square"
                />
              </div>
            </td>
            <td className="flex-grow px-4 py-2 text-center">
              {player.splashtag}
            </td>
            <td className="flex-grow px-4 py-2 text-center">
              <div className="flex flex-col sm:flex-row justify-center items-center gap-2">
                <div className="flex flex-wrap justify-center items-center gap-2">
                  <div className="min-w-[40px]">
                    <img
                      src={
                        player.prev_season_region ? TakorokaIcon : TentatekIcon
                      }
                      alt={`Player was in ${
                        player.prev_season_region ? "Takoroka" : "Tentatek"
                      } last season`}
                      className={`h-10 w-10 object-cover aspect-square`}
                    />
                  </div>
                  <div className="min-w-[40px]">
                    {player.diamond_x_count > 0 ? (
                      <DiamondBadge count={player.diamond_x_count} />
                    ) : (
                      <div className="h-10 w-10 invisible"></div>
                    )}
                  </div>
                  <div className="min-w-[40px]">
                    {player.gold_x_count > 0 ? (
                      <Top10Badge count={player.gold_x_count} />
                    ) : (
                      <div className="h-10 w-10 invisible"></div>
                    )}
                  </div>
                  <div className="min-w-[40px]">
                    {player.silver_x_count > 0 ? (
                      <Top500Badge count={player.silver_x_count} />
                    ) : (
                      <div className="h-10 w-10 invisible"></div>
                    )}
                  </div>
                </div>
              </div>
            </td>
            <td className="w-20 px-4 py-2 text-right xpower-text font-bold">
              <span className="text-purplelight text-lg">
                {player.x_power.toFixed(1).toString().slice(0, 2)}
              </span>
              <span className="text-sm">
                {player.x_power.toFixed(1).toString().slice(2)}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default PlayerTable;
