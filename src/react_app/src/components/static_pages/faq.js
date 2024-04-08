import React from "react";

const FAQ = () => {
  const faqData = [
    {
      question: "What is splat.top?",
      answer: (
        <p className="text-white">
          <span className="text-purplelight">splat.top</span> is a website that
          tracks the <span className="text-purplelight">Top 500</span> players
          in Splatoon 3 as reported by SplatNet3. The website also provides a
          history for each player's entire Top 500 journey and analytics on the
          state of the game via the Top 500.
        </p>
      ),
    },
    {
      question: "Why can't I find myself?",
      answer: (
        <p className="text-white">
          If you can't find yourself in the history, there's two possible
          reasons:
          <ul className="text-white list-disc pl-5">
            <li>
              <span className="text-purplelight">
                Just entered the Top 500:
              </span>{" "}
              The system updates every 10 minutes, so if you've just entered the
              Top 500, your history may not be immediately available.
            </li>
            <li>
              <span className="text-purplelight">Brief appearance:</span> If you
              were in the Top 500 for a short time, you may not find your
              history.
            </li>
          </ul>
        </p>
      ),
    },
    {
      question: "How often are the rankings updated?",
      answer: (
        <ul className="text-white list-disc pl-5">
          <li>
            <span className="text-purplelight">February 2023-August 2023:</span>{" "}
            Data was updated hourly. Special thanks to{" "}
            <a
              href="https://splatoon3.ink"
              className="text-purplelight underline"
            >
              splatoon3.ink
            </a>{" "}
            for providing the data.
          </li>
          <li>
            <span className="text-purplelight">August 2023-March 2024:</span>{" "}
            Updates occurred every fifteen minutes.
          </li>
          <li>
            <span className="text-purplelight">March 2024-present:</span> Data
            is now updated every ten minutes.
          </li>
        </ul>
      ),
    },
    {
      question: "Can I see my own ranking?",
      answer: (
        <p className="text-white">
          Yes, you can view your ranking if you've been in the Top 500. Search
          using any in-game name you had when you reached the Top 500.
          Alternatively, if you have your NPLN ID you can access your page
          directly via{" "}
          <span className="text-purplelight">
            splat.top/player/npln_id_goes_here
          </span>
          . Note: If you were briefly in the Top 500 and missed by our data
          collection, you won't find your ranking.
        </p>
      ),
    },
    {
      question: "Can I have access to the data? I want to analyze it myself.",
      answer: (
        <>
          <p className="text-white">
            <b className="text-purplelight">
              Access to the full dataset is limited.
            </b>{" "}
            Request access by contacting us with your intended use.
            Contributions to splat.top or the Splatoon community are key
            criteria for access. Being a top player or content creator is not
            enough.
          </p>
          <p className="text-white">
            <b className="text-purplelight">For students:</b> Academic projects
            can receive an anonymized data subset. Contact us on Discord or
            Twitter with project details.
          </p>
        </>
      ),
    },
    {
      question: "I own a website and I want to use your data. Can I?",
      answer: (
        <p className="text-white">
          We may provide an API endpoint for your data needs. Contact us on
          Discord, Twitter, or via a GitHub issue on our repository. Pull
          requests greatly increase the chance of support.
        </p>
      ),
    },
    {
      question:
        "I'm a content creator and I want to feature your website. Can I?",
      answer: (
        <p className="text-white">
          Yes, using data or analytics from{" "}
          <span className="text-purplelight">splat.top</span> is fine as long as
          you credit the website. We appreciate a mention or link to the site.
          If you'd like to collaborate, have a special data request, or would
          just like the analytics explained in more detail for a younger
          audience, contact us.
        </p>
      ),
    },
  ];

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-8 text-center text-purplelight">
        Frequently Asked Questions
      </h1>
      <div className="flex flex-col gap-8">
        {faqData.map((item, index) => (
          <div
            key={index}
            className="bg-gray-800 shadow-lg rounded-lg p-6 question-block"
          >
            <h2 className="text-2xl font-semibold mb-4 text-purplelight">
              {item.question}
            </h2>
            <div className="block">{item.answer}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default FAQ;
