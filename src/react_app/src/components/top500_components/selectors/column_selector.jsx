import { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";

const ColumnSelector = ({
  columnVisibility,
  setColumnVisibility,
  columnsConfig,
  disabled = false,
}) => {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const buttonRef = useRef(null);

  const handleToggle = (columnId) => {
    if (disabled) return;
    setColumnVisibility((prev) => ({
      ...prev,
      [columnId]: !prev[columnId],
    }));
  };

  useEffect(() => {
    const handleResize = () => {
      if (isOpen && dropdownRef.current && buttonRef.current) {
        const dropdownRect = dropdownRef.current.getBoundingClientRect();
        const buttonRect = buttonRef.current.getBoundingClientRect();
        const windowWidth = window.innerWidth;

        // Calculate the right edge of the dropdown
        const dropdownRightEdge = buttonRect.left + dropdownRect.width;

        if (dropdownRightEdge > windowWidth) {
          // If dropdown extends beyond the right edge of the window
          const overflowAmount = dropdownRightEdge - windowWidth;
          dropdownRef.current.style.left = `${
            buttonRect.left - overflowAmount
          }px`;
        } else {
          // Position dropdown aligned with the left edge of the button
          dropdownRef.current.style.left = `${buttonRect.left}px`;
        }

        // Ensure the dropdown doesn't extend beyond the left edge of the window
        if (parseFloat(dropdownRef.current.style.left) < 0) {
          dropdownRef.current.style.left = "0px";
        }

        dropdownRef.current.style.top = `${
          buttonRect.bottom + window.scrollY
        }px`;
      }
    };

    window.addEventListener("resize", handleResize);
    handleResize();

    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, [isOpen]);

  return (
    <div className="relative inline-block text-left mb-4">
      <div>
        <button
          ref={buttonRef}
          type="button"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          className={`inline-flex justify-center w-full rounded-md border border-gray-700 px-4 py-2 bg-gray-800 text-sm font-medium text-white ${
            disabled
              ? "opacity-50 cursor-not-allowed"
              : "hover:bg-gray-700 focus:outline-hidden focus:ring-2 focus:ring-offset-2 focus:ring-purple"
          }`}
          disabled={disabled}
        >
          {t("select_columns")}
          <svg
            className="-mr-1 ml-2 h-5 w-5"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      </div>

      {!disabled && isOpen && (
        <div
          ref={dropdownRef}
          className="fixed mt-2 w-56 rounded-md shadow-lg bg-gray-800 ring-1 ring-black ring-opacity-5 focus:outline-hidden"
          style={{ zIndex: 10 }}
        >
          <div className="py-1">
            {columnsConfig.map((column) => (
              <label
                key={column.id}
                className={`flex justify-start items-center px-4 py-2 text-sm text-white ${
                  disabled
                    ? "opacity-50 cursor-not-allowed"
                    : "hover:bg-gray-700 cursor-pointer"
                }`}
              >
                <input
                  type="checkbox"
                  checked={columnVisibility[column.id]}
                  onChange={() => handleToggle(column.id)}
                  className="mr-2"
                  disabled={disabled}
                />
                {t(column.title_key)}{" "}
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ColumnSelector;
