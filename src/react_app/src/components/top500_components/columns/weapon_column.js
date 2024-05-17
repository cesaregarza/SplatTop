export const id = "weapon";
export const title_key = "column_weapon_title";
export const isVisible = true;
export const headerClasses = null;
export const cellClasses = null;
export const render = (player, t) => (
  <div className="bg-black rounded-full flex justify-center items-center h-10 w-10 mx-auto">
    <img
      src={player.weapon_image}
      alt={t("column_weapon_not_supported")}
      className="h-10 w-10 object-cover aspect-square"
    />
  </div>
);
