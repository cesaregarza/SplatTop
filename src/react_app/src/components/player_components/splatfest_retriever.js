import axios from "axios";

export const fetchFestivalDates = async () => {
  try {
    const today = new Date().toDateString();
    const cachedData = localStorage.getItem("festivalDates");

    if (cachedData) {
      const { date, dates } = JSON.parse(cachedData);
      const cacheDate = new Date(date);
      const todayDate = new Date(today);
      const oneWeek = 7 * 24 * 60 * 60 * 1000; // One week in milliseconds
      if (todayDate - cacheDate < oneWeek) {
        const parsedDates = JSON.parse(dates);
        return parsedDates.map((date) => [
          new Date(date[0]),
          new Date(date[1]),
        ]);
      } else {
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
    );
    return dates;
  } catch (error) {
    throw new Error("Error fetching festival dates: " + error.message);
  }
};

export default fetchFestivalDates;
