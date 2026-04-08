import { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";

const ColumnSelector = ({
  columnVisibility,
  setColumnVisibility,
  columnsConfig,
  disabled = false,
  baseClass = "relative inline-block text-left",
  buttonClassName = "",
  menuClassName = "",
}) => {
  const { t } = useTranslation("main_page");
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  const handleToggle = (columnId) => {
    if (disabled) return;
    setColumnVisibility((prev) => ({
      ...prev,
      [columnId]: !prev[columnId],
    }));
  };

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    const handleClickOutside = (event) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  return (
    <div className={baseClass} ref={containerRef}>
      <div>
        <button
          type="button"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          className={`inline-flex w-full items-center justify-between rounded-md border border-gray-800 bg-gray-950/70 px-3 py-2.5 text-sm font-medium text-white ${
            disabled
              ? "opacity-50 cursor-not-allowed"
              : "hover:border-gray-700 hover:bg-gray-900 focus:outline-hidden focus:ring-2 focus:ring-purple"
          } ${buttonClassName}`}
          disabled={disabled}
          aria-expanded={isOpen}
          aria-haspopup="menu"
        >
          {t("select_columns")}
          <svg
            className="ml-2 h-5 w-5 shrink-0"
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
          className={`absolute right-0 top-full z-20 mt-2 min-w-[14rem] rounded-md border border-gray-800 bg-gray-950 shadow-lg shadow-black/40 focus:outline-hidden ${menuClassName}`}
        >
          <div className="py-1">
            {columnsConfig.map((column) => (
              <label
                key={column.id}
                className={`flex cursor-pointer items-center justify-start px-4 py-2 text-sm text-white ${
                  disabled
                    ? "opacity-50 cursor-not-allowed"
                    : "hover:bg-gray-900"
                }`}
              >
                <input
                  type="checkbox"
                  checked={columnVisibility[column.id]}
                  onChange={() => handleToggle(column.id)}
                  className="mr-2 accent-purple"
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
