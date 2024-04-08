import React from "react";

const About = () => {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-8 text-center text-purplelight">
        About splat.top
      </h1>
      <div className="bg-gray-800 shadow-lg rounded-lg p-6">
        <p className="text-white mb-4">
          <span className="text-purplelight">splat.top</span> is a website
          dedicated to tracking and analyzing the Top 500 players in Splatoon 3.
          Our goal is to provide a comprehensive and up-to-date resource for the
          competitive Splatoon community.
        </p>
        <p className="text-white mb-4">
          We started this project in February 2023 with the aim of creating a
          centralized platform for players to track their progress and compare
          their performance with others. Since then, we have continuously
          improved our data collection and analysis capabilities to provide the
          most accurate and insightful information possible. As part of this
          effort, we have developed a data pipeline that automatically updates
          our rankings every 10 minutes, ensuring that players always have
          access to the latest information. We are always looking into new ways
          to expand and enhance our offerings, so stay tuned for exciting
          updates in the future!
        </p>
        <div className="text-white mb-4">
          <p>
            The <span className="text-purplelight">splat.top</span> team is
            comprised of passionate Splatoon players and skilled developers who
            bring their expertise in software engineering, data analysis, and
            competitive gaming to the project. We are united by our love for the
            game and our desire to contribute to its growth and success. We also
            all touch every part of the project, from data collection to website
            design, so the following roles are not strictly defined and are more
            indicative of our main responsibilities.
          </p>
          <p>Some of our key contributors include:</p>
          <ul className="list-disc pl-5">
            <li>
              <span className="text-purplelight">Joy</span>, our lead developer,
              who spearheads the technical implementation and data pipeline. Joy
              is a seasoned software engineer with a background in data science.
            </li>
            <li>
              <span className="text-purplelight">Slushie</span>, our data
              analyst. Slushie is also the lead developer of the popular Discord
              bot Spyke.
            </li>
            <li>
              <span className="text-purplelight">hfcRed</span>, our web
              developer. hfcRed is an avid VR enthusiast and is well regarded in
              that community.
            </li>
          </ul>
          <p>
            Together, we are constantly collaborating and innovating to push the
            boundaries of what's possible in competitive gaming analytics.
          </p>
        </div>
        <h2 className="text-2xl font-semibold mb-4 text-purplelight">
          What We Offer
        </h2>
        <ul className="text-white list-disc pl-5 mb-4">
          <li>Real-time Top 500 rankings updated every 10 minutes</li>
          <li>Player profiles with detailed performance history</li>
          <li>In-depth analytics on the state of the game and meta trends</li>
        </ul>
        <h2 className="text-2xl font-semibold mb-4 text-purplelight">Our Mission</h2>
        <p className="text-white mb-4">
          Our mission is to support the growth and development of the
          competitive Splatoon scene by providing valuable insights and
          fostering a sense of community among players. We believe that by
          empowering players with knowledge and connecting them with each other,
          we can help elevate the game to new heights.
        </p>
        <h2 className="text-2xl font-semibold mb-4 text-purplelight">
          Get Involved
        </h2>
        <p className="text-white">
          If you share our passion for Splatoon and data analysis, we'd love to
          hear from you! Whether you're interested in contributing to the
          project, providing feedback, or just connecting with like-minded
          individuals, feel free to reach out to us on Discord, Twitter, or
          GitHub. Together, we can make{" "}
          <span className="text-purplelight">splat.top</span> the ultimate
          resource for the competitive Splatoon community.
        </p>
      </div>
    </div>
  );
};

export default About;
