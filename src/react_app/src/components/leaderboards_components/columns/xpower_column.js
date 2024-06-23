export const id = "xpower";
export const title_key = "column_peak_xpower_title";
export const isVisible = true;
export const headerClasses = "w-24 px-4 py-2";
export const cellClasses = "w-24 px-4 py-2 xpower-text font-bolt";
export const render = (player, t) => (
  <div className="min-w-[7ch]">
    <span className="text-purplelight text-lg">
      {player.max_x_power.toFixed(1).toString().slice(0, 2)}
    </span>
    <span className="text-sm">
      {player.max_x_power.toFixed(1).toString().slice(2)}
    </span>
  </div>
);
export const generateRender = (column_name) => {
  return (player, t) => {
    const value = player[column_name];
    if (value === null) {
      return <div className="min-w-[7ch]">--</div>;
    }
    const valueStr = value.toFixed(1).toString();
    const highlightLength = value >= 10000 ? 3 : 2;
    return (
      <div className="min-w-[7ch]">
        <span className="text-purplelight text-lg">
          {valueStr.slice(0, highlightLength)}
        </span>
        <span className="text-sm">{valueStr.slice(highlightLength)}</span>
      </div>
    );
  };
};
