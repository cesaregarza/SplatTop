export const id = "xpower";
export const title_key = "column_peak_xpower_title";
export const isVisible = true;
export const headerClasses =
  "w-28 px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-[0.18em] text-gray-400";
export const cellClasses = "w-28 px-4 py-3 text-right xpower-text";
export const render = (player, t) => (
  <div className="min-w-[7ch] tabular-nums">
    <span className="text-lg text-purplelight">
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
      return <div className="min-w-[7ch] tabular-nums">--</div>;
    }
    const valueStr = value.toFixed(1).toString();
    const highlightLength = value >= 10000 ? 3 : 2;
    return (
      <div className="min-w-[7ch] tabular-nums">
        <span className="text-lg text-purplelight">
          {valueStr.slice(0, highlightLength)}
        </span>
        <span className="text-sm">{valueStr.slice(highlightLength)}</span>
      </div>
    );
  };
};
