import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import SkillOffsetTab from "./analytics_components/skill_offset/tab";
import LorenzTab from "./analytics_components/lorenz/tab";
import "./analytics_components/analytics.css";

const Analytics = () => {
  const { t } = useTranslation("analytics");
  const [activeTab, setActiveTab] = useState("skill-offset");

  const tabComponents = {
    "skill_offset": <SkillOffsetTab />,
    "lorenz": <LorenzTab />
  };

  const renderTabContent = () => {
    return tabComponents[activeTab] || <SkillOffsetTab />;
  };

  return (
    <div className="flex flex-col min-h-screen bg-gray-900 text-white">
      <header className="text-3xl font-bold mb-4 text-center text-white py-4 bg-gray-800 shadow-lg">
        {t("page_title")}
      </header>
      <div className="grow container mx-auto px-4 py-8 overflow-auto">
        <div className="border-b border-gray-800 mb-4">
          <nav className="flex">
            {Object.keys(tabComponents).map(tabKey => (
              <button
                key={tabKey}
                onClick={() => setActiveTab(tabKey)}
                className={`text-white py-4 px-6 block hover:bg-gray-700 focus:outline-hidden ${activeTab === tabKey ? "bg-gray-700" : ""}`}
              >
                {t(`${tabKey}.tab_name`)}
              </button>
            ))}
          </nav>
        </div>
        <div className="p-4 bg-gray-800 rounded-lg shadow-inner">
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
};

export default Analytics;
