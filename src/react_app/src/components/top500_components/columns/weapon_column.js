export const id = "weapon";
export const name = "Weapon";
export const isVisible = true;
export const headerClasses = null;
export const cellClasses = null;
export const render = (player) => (
  <div className="bg-black rounded-full flex justify-center items-center h-10 w-10 mx-auto">
    <img
      src={player.weapon_image}
      alt="Weapon name not yet supported"
      className="h-10 w-10 object-cover aspect-square"
    />
  </div>
);
