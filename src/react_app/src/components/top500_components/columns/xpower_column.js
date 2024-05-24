export const id = "xpower";
export const title_key = "column_xpower_title";
export const isVisible = true;
export const headerClasses = "w-20 px-4 py-2 text-right";
export const cellClasses = "w-20 px-4 py-2 text-right xpower-text font-bolt";
export const render = (player, t) => (
  <>
    <span className="text-purplelight text-lg">
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
