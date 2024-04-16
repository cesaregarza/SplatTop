import axios from "axios";

export const fetchFestivalDates = async () => {
  try {
    const today = new Date().toDateString();
    const cachedData = localStorage.getItem("festivalDates");

    if (cachedData) {
      const { date, dates } = JSON.parse(cachedData);
      if (date === today) {
        // Parse each of the dates, not using JSON.parse
        const parsedDates = JSON.parse(dates);
        return parsedDates.map((date) => [
          new Date(date[0]),
          new Date(date[1]),
        ]);
      } else {
        // Remove expired cache
        localStorage.removeItem("festivalDates");
      }
    }

    const response = await axios.get(
      "https://splatoon3.ink/data/festivals.json"
    );
    const data = response.data;

    const festRecords = data.US.data.festRecords.nodes;
    const dates = festRecords.map((fest) => [
      new Date(fest.startTime),
      new Date(fest.endTime),
    ]);

    localStorage.setItem(
      "festivalDates",
      JSON.stringify({ date: today, dates: JSON.stringify(dates) })
    ); // Store dates as a stringified JSON
    return dates;
  } catch (error) {
    throw new Error("Error fetching festival dates: " + error.message);
  }
};

export default fetchFestivalDates;
