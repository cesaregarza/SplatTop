import React from 'react';
import Top500BadgeIcon from "../assets/icons/t500.png";

const Top500Badge = ({ count }) => {
    const badgeClasses = `badge-container h-10 w-10 ${count > 1 ? 'has-count' : ''}`;
    const shineClasses = `badge-shine ${count >= 500 ? 'high-value' : ''}`;
    
    return (
        <div className={badgeClasses}>
        <img src={Top500BadgeIcon} alt="Top 500 Badge" className="badge-image"/>
        {count > 1 && (
            <span className="badge-count">x{count}</span>
        )}
        <div className={shineClasses}></div>
        </div>
    );
    }

export default Top500Badge;