import React, { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import {
  getImageFromId,
  createTranslator,
} from "../player_components/weapon_helper_functions";

const WeaponSelector = ({
  onWeaponSelect,
  weaponReferenceData,
  weaponTranslations,
  initialWeaponId,
}) => {
  const { t } = useTranslation();
  const [selectedWeapon, setSelectedWeapon] = useState(
    initialWeaponId !== undefined && initialWeaponId !== null
      ? initialWeaponId.toString()
      : null
  );
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const dropdownRef = useRef(null);
  const inputRef = useRef(null);

  const translator = createTranslator(weaponReferenceData, weaponTranslations);
  const translateWeaponId = translator.translateWeaponId;
  const translateClassName = translator.translateClassName;

  const handleWeaponSelect = (weaponId) => {
    setSelectedWeapon(weaponId);
    onWeaponSelect(weaponId);
    setIsOpen(false);
    setSearchTerm("");
  };

  useEffect(() => {
    if (
      initialWeaponId !== undefined &&
      initialWeaponId !== null &&
      initialWeaponId.toString() !== selectedWeapon
    ) {
      setSelectedWeapon(initialWeaponId.toString());
    }
  }, [initialWeaponId, selectedWeapon]);

  const groupedWeapons = Object.values(weaponReferenceData).reduce(
    (acc, weapon) => {
      const translatedClass = translateClassName(weapon.class);
      if (!acc[translatedClass]) {
        acc[translatedClass] = [];
      }
      acc[translatedClass].push(weapon);
      return acc;
    },
    {}
  );

  const filteredWeapons = Object.entries(groupedWeapons).reduce(
    (acc, [className, weapons]) => {
      const filteredWeapons = weapons.filter((weapon) =>
        translateWeaponId(weapon.reference_id)
          .toLowerCase()
          .includes(searchTerm.toLowerCase())
      );
      if (filteredWeapons.length > 0) {
        acc[className] = filteredWeapons;
      }
      return acc;
    },
    {}
  );

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleInputFocus = () => {
    setIsOpen(true);
  };

  const handleInputChange = (e) => {
    setSearchTerm(e.target.value);
    setIsOpen(true);
  };

  return (
    <div className="relative inline-block w-64" ref={dropdownRef}>
      <div className="flex items-center justify-between w-full bg-gray-800 border border-gray-700 text-white py-2 px-3 rounded leading-tight">
        {selectedWeapon !== null && !isOpen && (
          <div className="flex items-center">
            <div className="bg-black rounded-full flex justify-center items-center h-10 w-10 mr-2">
              <img
                src={getImageFromId(selectedWeapon, weaponReferenceData)}
                alt={translateWeaponId(selectedWeapon)}
                className="h-10 w-10 object-cover aspect-square"
              />
            </div>
            <span>{translateWeaponId(selectedWeapon)}</span>
          </div>
        )}
        <input
          ref={inputRef}
          type="text"
          className={`bg-transparent outline-none ${
            selectedWeapon !== null && !isOpen ? "hidden" : "flex-grow"
          }`}
          placeholder={t("select_weapon")}
          value={searchTerm}
          onChange={handleInputChange}
          onFocus={handleInputFocus}
        />
        <svg
          className={`fill-current h-4 w-4 ml-2 cursor-pointer ${
            isOpen ? "transform rotate-180" : ""
          }`}
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          onClick={() => setIsOpen(!isOpen)}
        >
          <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
        </svg>
      </div>
      {isOpen && (
        <div className="absolute z-10 w-full mt-1 bg-gray-800 border border-gray-700 rounded shadow-lg max-h-60 overflow-y-auto">
          {Object.entries(filteredWeapons).map(
            ([weaponClass, weapons], index) => (
              <div key={`weapon-selector-group-${index}`}>
                <div className="px-3 py-2 font-bold text-gray-400">
                  {t(weaponClass)}
                </div>
                {weapons.map((weapon, weaponIndex) => (
                  <div
                    key={`weapon-selector-option-${index}-${weaponIndex}`}
                    className="flex items-center px-3 py-2 cursor-pointer hover:bg-gray-700"
                    onClick={() => handleWeaponSelect(weapon.reference_id)}
                  >
                    <div className="bg-black rounded-full flex justify-center items-center h-10 w-10 mr-2">
                      <img
                        src={getImageFromId(
                          weapon.reference_id,
                          weaponReferenceData
                        )}
                        alt={translateWeaponId(weapon.reference_id)}
                        className="h-10 w-10 object-cover aspect-square"
                      />
                    </div>
                    <span>{translateWeaponId(weapon.reference_id)}</span>
                  </div>
                ))}
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
};

export default WeaponSelector;
