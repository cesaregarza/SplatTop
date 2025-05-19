import React from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { FixedSizeList as List } from "react-window";

import { columnsConfig } from "./columns_config";

const PlayerTable = ({ players, columnVisibility }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const visibleColumns = columnsConfig.filter(
    (column) => columnVisibility[column.id]
  );

  const defaultHeaderClasses = "w-20 px-4 py-2 text-center";
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
        {data.visibleColumns.map((column, idx) => (
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
          {visibleColumns.map((column, index) => (
            <th
              key={index}
              className={column.headerClasses || defaultHeaderClasses}
            >
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
        itemData={{ players, visibleColumns }}
      >
        {Row}
      </List>
    </table>
  );
};

export default PlayerTable;
