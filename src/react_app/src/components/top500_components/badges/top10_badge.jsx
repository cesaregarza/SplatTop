import React from "react";
import Top10BadgeIcon from "../../../assets/icons/t10.png";

const Top10Badge = ({ count, disable = false, size = "h-10 w-10" }) => {
  const badgeClasses = `badge-container badge-gold ${size} ${
    count > 1 ? "has-count" : ""
  }`;
  const highValue = count >= 10 ? "higher-value" : "high-value";
  const badgeShineClasses = disable
    ? "badge-image"
    : `badge-image ${count >= 5 ? highValue : ""}`;
  return (
    <div className={badgeClasses}>
      <img
        src={Top10BadgeIcon}
        alt="Top 10 Badge"
        className={badgeShineClasses}
      />
      {count > 1 && <span className="badge-count">x{count}</span>}
    </div>
  );
};

export default Top10Badge;
