import React from "react";
import DiamondBadgeIcon from "../../../assets/icons/sorder.png";

const DiamondBadge = ({ count }) => {
  const badgeClasses = `badge-container badge-rainbow h-10 w-10 ${
    count > 1 ? "has-count" : ""
  }`;
  const badgeShineClasses = `badge-image high-value`;

  return (
    <div className={badgeClasses}>
      <img
        src={DiamondBadgeIcon}
        alt="Achived 4 Top 10s in one season Badge"
        className={badgeShineClasses}
      />
      {count > 1 && <span className="badge-count">x{count}</span>}
    </div>
  );
};

export default DiamondBadge;
