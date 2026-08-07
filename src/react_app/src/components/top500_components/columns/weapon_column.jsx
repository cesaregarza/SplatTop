export const id = "weapon";
export const title_key = "column_weapon_title";
export const isVisible = true;
export const headerClasses =
  "w-20 px-3 py-2.5 text-center text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-gray-300";
export const cellClasses = "w-20 px-3 py-2.5 text-center align-middle";
export const render = (player, t) => (
  <div className="mx-auto flex h-9 w-9 items-center justify-center rounded-full bg-black">
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
      <div className="mx-auto flex h-9 w-9 items-center justify-center rounded-full bg-black">
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
