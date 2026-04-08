import React from "react";
import { useTranslation } from "react-i18next";
import TakorokaIcon from "../../../assets/icons/takoroka.png";
import TentatekIcon from "../../../assets/icons/tentatek.png";

const regions = ["Tentatek", "Takoroka"];
const regionIcons = {
  Takoroka: TakorokaIcon,
  Tentatek: TentatekIcon,
};

const RegionSelector = ({
  selectedRegion,
  setSelectedRegion,
  showTitle = true,
  showLabels = false,
  buttonVariant = "default",
  baseClass = "mb-4 w-full sm:w-auto",
  buttonPadding = "px-4 py-2",
  imageWidth = "w-12",
  imageHeight = "h-12",
}) => {
  const { t } = useTranslation("main_page");

  const getButtonClasses = (region) => {
    const isSelected = selectedRegion === region;

    if (buttonVariant === "utility") {
      return `rounded-md border ${buttonPadding} ${
        isSelected
          ? "border-purple-500/60 bg-purple-950/40 text-white"
          : "border-gray-800 bg-gray-950/70 text-gray-200 hover:border-gray-700 hover:bg-gray-900"
      } flex min-w-0 justify-center items-center`;
    }

    return `m-1 px-4 py-2 rounded-md ${
      isSelected
        ? "bg-purpledark text-white hover:bg-purple"
        : "bg-gray-700 hover:bg-purple"
    } flex justify-center items-center`;
  };

  return (
    <div className={baseClass}>
      {showTitle && <h2 className="text-xl font-bold mb-2">{t("region")}</h2>}
      <div className="flex flex-wrap items-center gap-2">
        {regions.map((region) => (
          <button
            key={region}
            onClick={() => setSelectedRegion(region)}
            className={getButtonClasses(region)}
            aria-label={region}
            aria-pressed={selectedRegion === region}
          >
            <img
              src={regionIcons[region]}
              alt={region}
              className={`${imageWidth} ${imageHeight} object-cover aspect-square`}
            />
            {showLabels ? (
              <span className="ml-2 text-sm font-medium">{region}</span>
            ) : null}
          </button>
        ))}
      </div>
    </div>
  );
};

export default RegionSelector;
