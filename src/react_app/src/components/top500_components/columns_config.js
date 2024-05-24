import * as RankColumn from "./columns/rank_column";
import * as WeaponColumn from "./columns/weapon_column";
import * as SplashtagColumn from "./columns/splashtag_column";
import * as BadgesColumn from "./columns/badges_column";
import * as XPowerColumn from "./columns/xpower_column";

const columnsConfig = [
  RankColumn,
  WeaponColumn,
  SplashtagColumn,
  BadgesColumn,
  XPowerColumn,
];

const allModesColumns = [];
const snakeCaseModes = [
  "splat_zones",
  "tower_control",
  "rainmaker",
  "clam_blitz",
];
snakeCaseModes.forEach((mode) => {
  const weaponRender = WeaponColumn.generateRender(`${mode}_weapon_image`);
  const xPowerRender = XPowerColumn.generateRender(`${mode}_x_power`);
  allModesColumns.push({
    ...WeaponColumn,
    id: `${mode}_weapon`,
    render: weaponRender,
  });
  allModesColumns.push({
    ...XPowerColumn,
    id: `${mode}_x_power`,
    render: xPowerRender,
  });
});

const allModesColumnsConfig = [
  RankColumn,
  SplashtagColumn,
  ...allModesColumns,
  {
    ...XPowerColumn,
    id: "total_x_power",
    title_key: "column_total_x_power_title",
    render: XPowerColumn.generateRender("total_x_power"),
  },
];

export { columnsConfig, allModesColumnsConfig };
