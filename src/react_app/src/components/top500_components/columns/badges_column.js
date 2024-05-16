import React from "react";
import TakorokaIcon from "../../../assets/icons/takoroka.png";
import TentatekIcon from "../../../assets/icons/tentatek.png";
import DiamondBadge from "../badges/diamond_badge";
import Top10Badge from "../badges/top10_badge";
import Top500Badge from "../badges/top500_badge";

const DiamondBadgeMemo = React.memo(DiamondBadge);
const Top10BadgeMemo = React.memo(Top10Badge);
const Top500BadgeMemo = React.memo(Top500Badge);

export const id = "badges";
export const title_key = "column_badge_title";
export const isVisible = true;
export const headerClasses = "flex-grow px-4 py-2 text-center";
export const cellClasses = "flex-grow px-4 py-2 text-center";
export const render = (player, t) => {
  const prev_season_key = player.prev_season_region ?
    "player_was_in_takoroka_last_season" :
    "player_was_in_tentatek_last_season";
  return (
    <div className="flex flex-col sm:flex-row justify-center items-center gap-2">
      <div className="flex flex-wrap justify-center items-center gap-2">
        <div className="min-w-[40px]">
          <img
            src={player.prev_season_region ? TakorokaIcon : TentatekIcon}
            alt={t(prev_season_key)}
            className={`h-10 w-10 object-cover aspect-square`}
          />
        </div>
        <div className="min-w-[40px]">
          {player.diamond_x_count > 0 ? (
            <DiamondBadgeMemo count={player.diamond_x_count} />
          ) : (
            <div className="h-10 w-10 invisible"></div>
          )}
        </div>
        <div className="min-w-[40px]">
          {player.gold_x_count > 0 ? (
            <Top10BadgeMemo count={player.gold_x_count} />
          ) : (
            <div className="h-10 w-10 invisible"></div>
          )}
        </div>
        <div className="min-w-[40px]">
          {player.silver_x_count > 0 ? (
            <Top500BadgeMemo count={player.silver_x_count} />
          ) : (
            <div className="h-10 w-10 invisible"></div>
          )}
        </div>
      </div>
    </div>
  );
};
