import React, { useMemo } from "react";
import TakorokaIcon from "../../../assets/icons/takoroka.png";
import TentatekIcon from "../../../assets/icons/tentatek.png";

const regions = ["Tentatek", "Takoroka"];
const regionIcons = {
  Takoroka: TakorokaIcon,
  Tentatek: TentatekIcon,
};

const RegionSelector = ({ selectedRegion, setSelectedRegion }) => {
  const regionButtons = useMemo(
    () =>
      regions.map((region) => (
        <button
          key={region}
          onClick={() => setSelectedRegion(region)}
          className={`m-1 px-4 py-2 rounded-md ${
            selectedRegion === region
              ? "bg-purpledark text-white hover:bg-purple"
              : "bg-gray-700 hover:bg-purple"
          } flex justify-center items-center`}
        >
          <img
            src={regionIcons[region]}
            alt={region}
            className="h-12 w-12 object-cover aspect-square"
          />
        </button>
      )),
    [selectedRegion, setSelectedRegion]
  );

  return (
    <div className="mb-4 w-full sm:w-auto">
      <h2 className="text-xl font-bold mb-2">Regions</h2>
      <div className="flex flex-wrap justify-center items-center">
        {regionButtons}
      </div>
    </div>
  );
};

export default RegionSelector;
