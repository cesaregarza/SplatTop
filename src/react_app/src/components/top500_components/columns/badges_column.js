import TakorokaIcon from "../../../assets/icons/takoroka.png";
import TentatekIcon from "../../../assets/icons/tentatek.png";
import DiamondBadge from "../badges/diamond_badge";
import Top10Badge from "../badges/top10_badge";
import Top500Badge from "../badges/top500_badge";

export const name = "Badges";
export const headerClasses = "flex-grow px-4 py-2 text-center";
export const cellClasses = "flex-grow px-4 py-2 text-center";
export const render = (player) => (
  <div className="flex flex-col sm:flex-row justify-center items-center gap-2">
    <div className="flex flex-wrap justify-center items-center gap-2">
      <div className="min-w-[40px]">
        <img
          src={player.prev_season_region ? TakorokaIcon : TentatekIcon}
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
);
