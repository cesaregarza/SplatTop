import React from "react";
import Top10BadgeIcon from "../../../assets/icons/t10.png";
import Top500BadgeIcon from "../../../assets/icons/t500.png";
import Top10Badge from "./top10_badge";
import Top500Badge from "./top500_badge";

const CombinedBadge = ({
  top10Count,
  top500Count,
  size = "h-10 w-10",
  disable = false,
}) => {
  if (top10Count === 0 && top500Count === 0) {
    return null;
  }
  if (top10Count == 0) {
    return <Top500Badge count={top500Count} disable={disable} size={size} />;
  }

  const noSliceClass = top500Count == 0 ? "no-slice" : "";
  const top10BadgeShineClass = disable
    ? "badge-image"
    : `badge-image ${
        top10Count >= 5
          ? top10Count >= 10
            ? "badge-gold higher-value"
            : "badge-gold high-value"
          : ""
      }`;
  const top500BadgeShineClass = disable
    ? "badge-image"
    : `badge-image ${top500Count >= 20 ? "high-value" : ""}`;

  return (
    <div className={`combined-badge ${size}`}>
      {top10Count > 1 && (
        <div className="badge-count-wrapper badge-count-wrapper-gold">
          <span className="badge-count">x{top10Count}</span>
        </div>
      )}
      <div className={`badge-slice badge-slice-gold ${noSliceClass}`}>
        <img
          src={Top10BadgeIcon}
          alt="Top 10 Badge"
          className={top10BadgeShineClass}
        />
      </div>
      <div className={`badge-slice badge-slice-silver ${noSliceClass}`}>
        <img
          src={Top500BadgeIcon}
          alt="Top 500 Badge"
          className={top500BadgeShineClass}
        />
      </div>
      {top500Count > 1 && (
        <div className="badge-count-wrapper badge-count-wrapper-silver">
          <span className="badge-count">x{top500Count}</span>
        </div>
      )}
    </div>
  );
};

export default CombinedBadge;
