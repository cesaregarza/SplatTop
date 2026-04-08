export const id = "weapon";
export const title_key = "column_weapon_title";
export const isVisible = true;
export const headerClasses =
  "w-20 px-3 py-2.5 text-center text-xs font-semibold uppercase tracking-[0.18em] text-gray-400";
export const cellClasses = "w-20 px-3 py-3 text-center";
export const render = (player, t) => (
  <div className="bg-black rounded-full flex justify-center items-center h-9 w-9 mx-auto">
    <img
      src={player.weapon_image}
      alt={t("column_weapon_not_supported")}
      className="h-9 w-9 object-cover aspect-square"
    />
  </div>
);

export const generateRender = (column_name) => {
  return (player, t) => {
    const src = player[column_name];
    return (
      <div className="bg-black rounded-full flex justify-center items-center h-9 w-9 mx-auto">
        {src ? (
          <img
            src={src}
            alt={t("column_weapon_not_supported")}
            className="h-9 w-9 object-cover aspect-square"
          />
        ) : (
          "--"
        )}
      </div>
    );
  };
};
