import React from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { FixedSizeList as List } from "react-window";

import { allModesColumnsConfig } from "./columns_config";
import SplatZonesIcon from "../../assets/icons/splat_zones.png";
import TowerControlIcon from "../../assets/icons/tower_control.png";
import RainmakerIcon from "../../assets/icons/rainmaker.png";
import ClamBlitzIcon from "../../assets/icons/clam_blitz.png";
import AllModesIcon from "../../assets/icons/all_modes.png";

const modeIcons = {
  splat_zones: SplatZonesIcon,
  tower_control: TowerControlIcon,
  rainmaker: RainmakerIcon,
  clam_blitz: ClamBlitzIcon,
  total: AllModesIcon,
};

const AllModesTable = ({ players }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const headerClasses = "w-20 px-4 py-2 text-center border border-gray-600";
  const defaultCellClasses = "w-20 px-4 py-2 text-center";

  const handleRowClick = (playerId) => {
    navigate(`/player/${playerId}`);
    window.scrollTo(0, 0);
  };

  const Row = ({ index, style, data }) => {
    const player = data.players[index];
    return (
      <tr
        style={style}
        className="border-b border-gray-700 hover:bg-purpledark cursor-pointer"
        onClick={() => handleRowClick(player.player_id)}
      >
        {allModesColumnsConfig.map((column, idx) => (
          <td
            key={idx}
            className={column.cellClasses || defaultCellClasses}
          >
            {column.render(player, t)}
          </td>
        ))}
      </tr>
    );
  };

  const TBody = React.forwardRef((props, ref) => (
    <tbody ref={ref} {...props} />
  ));

  const rowHeight = 52;

  return (
    <table className="table-auto w-full bg-gray-800">
      <thead>
        <tr className="bg-gray-700">
          <th className={headerClasses} rowSpan={2}>
            {t("Rank")}
          </th>
          <th className={headerClasses} rowSpan={2}>
            {t("Splashtag")}
          </th>
          <th className={headerClasses} colSpan={2}>
            <img
              src={modeIcons.splat_zones}
              alt="splat_zones"
              className="w-6 h-6 mx-auto"
            />
          </th>
          <th className={headerClasses} colSpan={2}>
            <img
              src={modeIcons.tower_control}
              alt="tower_control"
              className="w-6 h-6 mx-auto"
            />
          </th>
          <th className={headerClasses} colSpan={2}>
            <img
              src={modeIcons.rainmaker}
              alt="rainmaker"
              className="w-6 h-6 mx-auto"
            />
          </th>
          <th className={headerClasses} colSpan={2}>
            <img
              src={modeIcons.clam_blitz}
              alt="clam_blitz"
              className="w-6 h-6 mx-auto"
            />
          </th>
          <th className={headerClasses}>
            <img
              src={modeIcons.total}
              alt="total"
              className="w-6 h-6 mx-auto"
            />
          </th>
        </tr>
        <tr className="bg-gray-700">
          {allModesColumnsConfig.slice(2).map((column, index) => (
            <th key={index} className={headerClasses}>
              {t(column.title_key)}
            </th>
          ))}
        </tr>
      </thead>
      <List
        height={Math.min(players.length, 10) * rowHeight}
        itemCount={players.length}
        itemSize={rowHeight}
        width="100%"
        outerElementType={TBody}
        itemData={{ players }}
      >
        {Row}
      </List>
    </table>
  );
};

export default AllModesTable;
