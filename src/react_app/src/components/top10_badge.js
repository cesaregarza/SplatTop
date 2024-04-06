import React from 'react';
import Top10BadgeIcon from "../assets/icons/t10.png";

const Top10Badge = ({ count }) => {
  const badgeClasses = `badge-container h-10 w-10 ${count > 1 ? 'has-count' : ''}`;
  const shineClasses = `badge-shine ${count >= 10 ? 'high-value' : ''}`;

  return (
    <div className={badgeClasses}>
      <img src={Top10BadgeIcon} alt="Top 10 Badge" className="badge-image"/>
      {count > 1 && (
        <span className="badge-count">x{count}</span>
      )}
      <div className={shineClasses}></div>
    </div>
  );
};

export default Top10Badge;