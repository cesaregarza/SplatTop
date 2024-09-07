import React, { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import {
  getImageFromId,
  createTranslator,
} from "../player_components/weapon_helper_functions";
import { FaTimes } from "react-icons/fa";

const WeaponSelector = ({
  onWeaponSelect,
  weaponReferenceData,
  weaponTranslations,
  initialWeaponId,
  allowNull = false,
}) => {
  const { t } = useTranslation("weapon_leaderboard");
  const [selectedWeapon, setSelectedWeapon] = useState(
    initialWeaponId !== undefined && initialWeaponId !== null
      ? initialWeaponId.toString()
      : null
  );
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const dropdownRef = useRef(null);
  const inputRef = useRef(null);
  const scrollRef = useRef(null);

  const translator = createTranslator(weaponReferenceData, weaponTranslations);
  const translateWeaponId = translator.translateWeaponId;
  const translateClassName = translator.translateClassName;

  const handleWeaponSelect = (weaponId) => {
    setSelectedWeapon(weaponId);
    onWeaponSelect(weaponId);
    setIsOpen(false);
    setSearchTerm("");
  };

  const handleClearWeapon = (e) => {
    e.stopPropagation();
    setSelectedWeapon(null);
    onWeaponSelect(null);
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

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  const handleInputFocus = () => {
    setIsOpen(true);
  };

  const handleInputChange = (e) => {
    setSearchTerm(e.target.value);
    setIsOpen(true);
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  };

  const toggleDropdown = () => {
    setIsOpen(!isOpen);
    if (!isOpen) {
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  };

  const handleKeyDown = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  };

  return (
    <div className="relative inline-block w-64" ref={dropdownRef}>
      <div
        className="flex items-center justify-between w-full bg-gray-800 border border-gray-700 text-white py-2 px-3 rounded leading-tight cursor-pointer"
        onClick={toggleDropdown}
      >
        {selectedWeapon !== null && !isOpen ? (
          <div className="flex items-center flex-grow">
            <div className="bg-black rounded-full flex justify-center items-center h-10 w-10 mr-2">
              <img
                src={getImageFromId(selectedWeapon, weaponReferenceData)}
                alt={translateWeaponId(selectedWeapon)}
                className="h-10 w-10 object-cover aspect-square"
              />
            </div>
            <span>{translateWeaponId(selectedWeapon)}</span>
            {allowNull && (
              <button
                onClick={handleClearWeapon}
                className="ml-auto p-1 hover:bg-gray-700 rounded"
                aria-label="Clear weapon selection"
              >
                <FaTimes size={14} />
              </button>
            )}
          </div>
        ) : (
          <input
            ref={inputRef}
            type="text"
            className="bg-transparent outline-none flex-grow h-10"
            placeholder={t("select_weapon")}
            value={searchTerm}
            onChange={handleInputChange}
            onFocus={handleInputFocus}
            onClick={(e) => e.stopPropagation()}
            onKeyDown={handleKeyDown}
          />
        )}
        <svg
          className={`fill-current h-4 w-4 ml-2 ${
            isOpen ? "transform rotate-180" : ""
          }`}
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
        >
          <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
        </svg>
      </div>
      {isOpen && (
        <div
          ref={scrollRef}
          className="absolute z-10 w-full mt-1 bg-gray-800 border border-gray-700 rounded shadow-lg max-h-60 overflow-y-auto"
        >
          {allowNull && (
            <div
              className="flex items-center px-3 py-2 cursor-pointer hover:bg-gray-700"
              onClick={() => handleWeaponSelect(null)}
            >
              <span>{t("null_selection")}</span>
            </div>
          )}
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
