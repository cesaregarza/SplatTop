export const id = "xpower";
export const title_key = "column_xpower_title";
export const isVisible = true;
export const headerClasses =
  "w-28 px-4 py-2.5 text-right text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-gray-300";
export const cellClasses =
  "w-28 px-4 py-2.5 text-right align-middle xpower-text tabular-nums";
export const render = (player, t) => (
  <>
    <span className="text-lg text-purplelight">
      {player.x_power.toFixed(1).toString().slice(0, 2)}
    </span>
    <span className="text-sm">
      {player.x_power.toFixed(1).toString().slice(2)}
    </span>
  </>
);
export const generateRender = (column_name) => {
  return (player, t) => {
    const value = player[column_name];
    if (value === null) {
      return "--";
    }
    const valueStr = value.toFixed(1).toString();
    const highlightLength = value >= 10000 ? 3 : 2;
    return (
      <>
        <span className="text-purplelight text-lg">
          {valueStr.slice(0, highlightLength)}
        </span>
        <span className="text-sm">{valueStr.slice(highlightLength)}</span>
      </>
    );
  };
};
