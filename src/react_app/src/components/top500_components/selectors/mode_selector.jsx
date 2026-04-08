import React from "react";
import { useTranslation } from "react-i18next";
import SplatZonesIcon from "../../../assets/icons/splat_zones.png";
import TowerControlIcon from "../../../assets/icons/tower_control.png";
import RainmakerIcon from "../../../assets/icons/rainmaker.png";
import ClamBlitzIcon from "../../../assets/icons/clam_blitz.png";
import AllModesIcon from "../../../assets/icons/all_modes.png";
import { modeKeyMap, modes } from "../../constants";

const modeIcons = {
  "Splat Zones": SplatZonesIcon,
  "Tower Control": TowerControlIcon,
  Rainmaker: RainmakerIcon,
  "Clam Blitz": ClamBlitzIcon,
  "All Modes": AllModesIcon,
};

const GRID_GAP_PX = 8;

const getAutoFitEqualWidthColumnCount = ({
  buttonCount,
  containerWidth,
  contentWidths,
  chromeWidth,
  gapPx = GRID_GAP_PX,
}) => {
  if (buttonCount !== 4 || !containerWidth || contentWidths.length !== 4) {
    return 2;
  }

  const requiredButtonWidth = Math.max(...contentWidths) + chromeWidth;
  const requiredWidth =
    requiredButtonWidth * buttonCount + gapPx * (buttonCount - 1);

  return requiredWidth <= containerWidth ? 4 : 2;
};

const ModeSelector = ({
  selectedMode,
  setSelectedMode,
  allowedModes = [true, true, true, true],
  showTitle = true,
  modeButtonSize = "",
  buttonPadding = "px-4 py-2",
  imageWidth = "w-12",
  imageHeight = "h-12",
  baseClass = "mb-4 w-full sm:w-auto",
  includeAllModes = false,
  showLabels = false,
  buttonVariant = "default",
  equalWidthButtons = false,
  equalWidthGridClassName = "grid-cols-2",
  autoFitEqualWidth = false,
}) => {
  const { t } = useTranslation();
  const gridRef = React.useRef(null);
  const buttonRefs = React.useRef([]);
  const contentRefs = React.useRef([]);
  const [resolvedColumnCount, setResolvedColumnCount] = React.useState(2);

  const displayedModes = React.useMemo(
    () => (includeAllModes ? [...modes, "All Modes"] : modes),
    [includeAllModes]
  );

  const getModeLabel = React.useCallback(
    (mode) => t(modeKeyMap[mode], { ns: "game", defaultValue: mode }),
    [t]
  );

  const getButtonClasses = (mode, isAllowed = true) => {
    const isSelected = selectedMode === mode;

    if (buttonVariant === "utility") {
      return `rounded-md border ${buttonPadding} ${modeButtonSize} ${
        isSelected
          ? "border-purple-500/60 bg-purple-950/40 text-white"
          : "border-gray-800 bg-gray-950/70 text-gray-200 hover:border-gray-700 hover:bg-gray-900"
      } flex justify-center items-center ${
        equalWidthButtons ? "h-full min-h-[3.5rem] w-full min-w-0" : ""
      } ${
        !isAllowed ? "cursor-not-allowed opacity-45 grayscale" : ""
      }`;
    }

    return `m-1 rounded-md ${buttonPadding} ${modeButtonSize} ${
      isSelected
        ? "bg-purpledark text-white hover:bg-purple"
        : "bg-gray-700 hover:bg-purple"
    } flex justify-center items-center ${
      !isAllowed ? "grayscale cursor-not-allowed" : ""
    }`;
  };

  const measureGridFit = React.useCallback(() => {
    if (!equalWidthButtons || !autoFitEqualWidth || displayedModes.length !== 4) {
      return;
    }

    const containerWidth = gridRef.current?.clientWidth ?? 0;
    const firstButton = buttonRefs.current.find(Boolean);
    const contentWidths = contentRefs.current
      .slice(0, displayedModes.length)
      .filter(Boolean)
      .map((node) => node.scrollWidth);

    if (!firstButton || contentWidths.length !== 4 || containerWidth === 0) {
      setResolvedColumnCount(2);
      return;
    }

    const computedStyle = window.getComputedStyle(firstButton);
    const chromeWidth =
      parseFloat(computedStyle.paddingLeft || 0) +
      parseFloat(computedStyle.paddingRight || 0) +
      parseFloat(computedStyle.borderLeftWidth || 0) +
      parseFloat(computedStyle.borderRightWidth || 0);

    setResolvedColumnCount(
      getAutoFitEqualWidthColumnCount({
        buttonCount: displayedModes.length,
        containerWidth,
        contentWidths,
        chromeWidth,
      })
    );
  }, [autoFitEqualWidth, displayedModes.length, equalWidthButtons]);

  React.useLayoutEffect(() => {
    measureGridFit();

    if (!equalWidthButtons || !autoFitEqualWidth || displayedModes.length !== 4) {
      return undefined;
    }

    const handleResize = () => {
      measureGridFit();
    };

    window.addEventListener("resize", handleResize);

    let resizeObserver;
    if (typeof ResizeObserver !== "undefined" && gridRef.current) {
      resizeObserver = new ResizeObserver(handleResize);
      resizeObserver.observe(gridRef.current);
    }

    return () => {
      window.removeEventListener("resize", handleResize);
      resizeObserver?.disconnect();
    };
  }, [autoFitEqualWidth, displayedModes.length, equalWidthButtons, measureGridFit]);

  const gridClassName = equalWidthButtons
    ? `grid auto-rows-fr gap-2 ${
        autoFitEqualWidth && displayedModes.length === 4
          ? resolvedColumnCount === 4
            ? "grid-cols-4"
            : "grid-cols-2"
          : equalWidthGridClassName
      }`
    : "flex flex-wrap items-center gap-2";

  return (
    <div className={baseClass}>
      {showTitle && <h2 className="text-xl font-bold mb-2">{t("modes")}</h2>}
      <div ref={gridRef} className={gridClassName}>
        {displayedModes.map((mode, index) => {
          const isAllowed =
            mode === "All Modes" ? true : allowedModes[modes.indexOf(mode)];

          return (
            <div
              key={mode}
              className={
                equalWidthButtons ? "min-w-0 h-full" : "flex justify-center"
              }
            >
              <button
                ref={(node) => {
                  buttonRefs.current[index] = node;
                }}
                onClick={() => (isAllowed ? setSelectedMode(mode) : null)}
                className={getButtonClasses(mode, isAllowed)}
                disabled={!isAllowed}
                title={
                  !isAllowed ? "No data found for this mode" : getModeLabel(mode)
                }
                aria-label={getModeLabel(mode)}
                aria-pressed={selectedMode === mode}
              >
                <div
                  ref={(node) => {
                    contentRefs.current[index] = node;
                  }}
                  className={`flex items-center justify-center ${
                    equalWidthButtons ? "w-full min-w-0" : ""
                  }`}
                >
                  <img
                    src={modeIcons[mode]}
                    alt={mode}
                    className={`${imageWidth} ${imageHeight} object-cover aspect-square`}
                  />
                  {showLabels ? (
                    <span
                      className={`ml-2 text-sm font-medium ${
                        equalWidthButtons
                          ? "min-w-0 flex-1 text-left leading-tight whitespace-normal"
                          : ""
                      }`}
                    >
                      {getModeLabel(mode)}
                    </span>
                  ) : null}
                </div>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export { getAutoFitEqualWidthColumnCount };
export default ModeSelector;
