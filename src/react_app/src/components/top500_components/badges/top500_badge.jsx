import React from "react";
import Top500BadgeIcon from "../../../assets/icons/t500.png";

const Top500Badge = ({ count, disable = false, size = "h-10 w-10" }) => {
  const badgeClasses = `badge-container badge-silver ${size} ${
    count > 1 ? "has-count" : ""
  }`;
  const badgeShineClasses = disable
    ? "badge-image"
    : `badge-image ${count >= 20 ? "high-value" : ""}`;

  return (
    <div className={badgeClasses}>
      <img
        src={Top500BadgeIcon}
        alt="Top 500 Badge"
        className={badgeShineClasses}
      />
      {count > 1 && <span className="badge-count">x{count}</span>}
    </div>
  );
};

export default Top500Badge;
