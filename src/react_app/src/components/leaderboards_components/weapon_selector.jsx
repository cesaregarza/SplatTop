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
}) => {
  const { t } = useTranslation();
  const [selectedWeapon, setSelectedWeapon] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const translator = createTranslator(weaponReferenceData, weaponTranslations);
  const translateWeaponId = translator.translateWeaponId;
  const translateClassName = translator.translateClassName;

  const handleWeaponSelect = (weaponId) => {
    setSelectedWeapon(weaponId);
    onWeaponSelect(weaponId);
    setIsOpen(false);
  };

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

  return (
    <div className="relative inline-block w-64" ref={dropdownRef}>
      <div
        className="flex items-center justify-between w-full bg-gray-800 border border-gray-700 text-white py-2 px-3 rounded leading-tight cursor-pointer"
        onClick={() => setIsOpen(!isOpen)}
      >
        {selectedWeapon ? (
          <>
            <div className="bg-black rounded-full flex justify-center items-center h-10 w-10 mr-2">
              <img
                src={getImageFromId(selectedWeapon, weaponReferenceData)}
                alt={translateWeaponId(selectedWeapon)}
                className="h-10 w-10 object-cover aspect-square"
              />
            </div>
            <span>{translateWeaponId(selectedWeapon)}</span>
          </>
        ) : (
          <span>{t("select_weapon")}</span>
        )}
        <svg
          className="fill-current h-4 w-4 ml-2"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
        >
          <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
        </svg>
      </div>
      {isOpen && (
        <div className="absolute z-10 w-full mt-1 bg-gray-800 border border-gray-700 rounded shadow-lg max-h-60 overflow-y-auto">
          {Object.entries(groupedWeapons).map(
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
