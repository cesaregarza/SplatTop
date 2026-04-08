import * as RankColumn from "./columns/rank_column";
import * as WeaponColumn from "./columns/weapon_column";
import * as SplashtagColumn from "./columns/splashtag_column";
import * as XPowerColumn from "./columns/xpower_column";
import * as PercentColumn from "./columns/percent_used_column";
import * as SeasonNumberColumn from "./columns/season_number_column";

const getColumnsConfig = ({ showWeaponColumn = true } = {}) => {
  const columns = [
    RankColumn,
    SplashtagColumn,
    XPowerColumn,
    PercentColumn,
    SeasonNumberColumn,
  ];

  if (showWeaponColumn) {
    columns.splice(1, 0, WeaponColumn);
  }

  return columns;
};

export { getColumnsConfig };
