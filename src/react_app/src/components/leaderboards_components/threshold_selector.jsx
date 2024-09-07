import React, { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

const ThresholdSelector = ({ threshold, setThreshold }) => {
  const { t } = useTranslation("weapon_leaderboard");
  const [isDragging, setIsDragging] = useState(false);
  const [dragValue, setDragValue] = useState(threshold);
  const containerRef = useRef(null);
  const circleRef = useRef(null);

  useEffect(() => {
    setDragValue(threshold);
  }, [threshold]);

  const handleMouseDown = (event) => {
    event.preventDefault();
    setIsDragging(true);
    updateValueFromEvent(event);
  };

  const handleMouseMove = (event) => {
    if (isDragging) {
      updateValueFromEvent(event);
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setThreshold(dragValue);
  };

  const updateValueFromEvent = (event) => {
    if (containerRef.current) {
      const containerRect = containerRef.current.getBoundingClientRect();
      const newX = event.clientX - containerRect.left;
      const containerWidth = containerRect.width;
      const newValue = Math.round((newX / containerWidth) * 1000);
      const clampedValue = Math.max(0, Math.min(1000, newValue));
      setDragValue(clampedValue);
    }
  };

  useEffect(() => {
    if (isDragging) {
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
    }
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, dragValue]); // eslint-disable-line react-hooks/exhaustive-deps

  // Touch event handlers
  const handleTouchStart = (event) => {
    event.preventDefault();
    setIsDragging(true);
    updateValueFromTouchEvent(event);
  };

  const handleTouchMove = (event) => {
    if (isDragging) {
      updateValueFromTouchEvent(event);
    }
  };

  const handleTouchEnd = () => {
    setIsDragging(false);
    setThreshold(dragValue);
  };

  const updateValueFromTouchEvent = (event) => {
    if (containerRef.current) {
      const containerRect = containerRef.current.getBoundingClientRect();
      const newX = event.touches[0].clientX - containerRect.left;
      const containerWidth = containerRect.width;
      const newValue = Math.round((newX / containerWidth) * 1000);
      const clampedValue = Math.max(0, Math.min(1000, newValue));
      setDragValue(clampedValue);
    }
  };

  useEffect(() => {
    if (isDragging) {
      window.addEventListener("touchmove", handleTouchMove);
      window.addEventListener("touchend", handleTouchEnd);
    }
    return () => {
      window.removeEventListener("touchmove", handleTouchMove);
      window.removeEventListener("touchend", handleTouchEnd);
    };
  }, [isDragging, dragValue]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="w-full max-w-3xl mx-auto bg-gray-900 p-4 rounded-lg">
      <label
        htmlFor="threshold"
        className="block text-lg font-semibold text-gray-300 mb-2"
      >
        {t("threshold_select")}
      </label>
      <div 
        className="relative h-8" 
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onTouchStart={handleTouchStart}
      >
        <div className="absolute top-1/2 -translate-y-1/2 left-0 right-0 h-1 bg-gray-700 rounded-full">
          <div
            className="absolute top-0 left-0 h-full bg-purple rounded-full"
            style={{ width: `${dragValue / 10}%` }}
          />
        </div>
        <div
          ref={circleRef}
          className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-purple rounded-full shadow-lg cursor-pointer flex items-center justify-center"
          style={{ left: `calc(${dragValue / 10}% - 8px)` }}
        >
          <div className="w-3 h-3 bg-purple rounded-full" />
        </div>
      </div>
      <div className="text-right mt-2">
        <span className="text-lg font-bold text-white">
          {(dragValue / 10).toFixed(1)}%
        </span>
      </div>
    </div>
  );
};

export default ThresholdSelector;
