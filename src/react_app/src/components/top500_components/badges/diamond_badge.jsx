import React from "react";
import DiamondBadgeIcon from "../../../assets/icons/diamond_1.png";

const DiamondBadge = ({ count, disable = false, size = "h-10 w-10" }) => {
  const badgeClasses = `badge-container badge-rainbow ${size} ${
    count > 1 ? "has-count" : ""
  }`;
  const badgeShineClasses = disable
    ? "badge-image"
    : `badge-image high-value`;

  return (
    <div className={badgeClasses}>
      <img
        src={DiamondBadgeIcon}
        alt="Achieved 4 Top 10s in one season Badge"
        className={badgeShineClasses}
      />
      {count > 1 && <span className="badge-count">x{count}</span>}
    </div>
  );
};

export default DiamondBadge;
