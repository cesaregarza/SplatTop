import React from "react";

const PercentageCircle = ({ percentage }) => {
  const radius = 10;
  const circumference = 2 * Math.PI * radius;
  const fillPercentage = ((100 - percentage) / 100) * circumference;

  return (
    <div className="flex items-center">
      <svg width="24" height="24" viewBox="0 0 24 24" className="mr-2">
        <defs>
          <filter id="antialiasing">
            <feGaussianBlur in="SourceGraphic" stdDeviation="0.2" />
          </filter>
        </defs>
        <circle
          cx="12"
          cy="12"
          r={radius}
          fill="none"
          stroke="#e0e0e0"
          strokeWidth="3"
          filter="url(#antialiasing)"
        />
        <circle
          cx="12"
          cy="12"
          r={radius}
          fill="none"
          stroke="#ab5ab7"
          strokeWidth="4"
          strokeDasharray={circumference}
          strokeDashoffset={fillPercentage}
          transform="rotate(-90 12 12)"
          strokeLinecap="round"
          filter="url(#antialiasing)"
        />
      </svg>
      <span>{percentage.toFixed(1)}%</span>
    </div>
  );
};

export default PercentageCircle;
