export const id = "xpower";
export const name = "XPower";
export const isVisible = true;
export const headerClasses = "w-20 px-4 py-2 text-right";
export const cellClasses = "w-20 px-4 py-2 text-right xpower-text font-bolt";
export const render = (player) => (
  <>
    <span className="text-purplelight text-lg">
      {player.x_power.toFixed(1).toString().slice(0, 2)}
    </span>
    <span className="text-sm">
      {player.x_power.toFixed(1).toString().slice(2)}
    </span>
  </>
);
