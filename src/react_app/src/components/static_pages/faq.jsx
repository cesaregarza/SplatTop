import React from "react";
import { useTranslation } from "react-i18next";

const FAQ = () => {
  const { t } = useTranslation("faq");

  const faqData = t("faq.questions", { returnObjects: true });

  document.title = t("faq.title");

  return (
    <div className="container mx-auto px-4 py-8 bg-gray-800">
      <h1 className="text-4xl font-bold mb-8 text-center text-purplelight">
        {t("faq.title")}
      </h1>
      <div className="flex flex-col gap-8">
        {faqData &&
          faqData.map((item, index) => (
            <div
              key={index}
              className="bg-gray-800 shadow-lg rounded-lg p-6 question-block"
            >
              <h2 className="text-2xl font-semibold mb-4 text-purplelight">
                {item.question}
              </h2>
              <div className="block">
                <div dangerouslySetInnerHTML={{ __html: t(item.answer) }} />
              </div>
            </div>
          ))}
      </div>
    </div>
  );
};

export default FAQ;
