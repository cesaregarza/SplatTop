import React, { useEffect, useState } from "react";
import axios from "axios";
import Loading from "./loading";

const Top500 = () => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      const apiUrl = process.env.REACT_APP_API_URL || "";
      const endpoint = `${apiUrl}/api/leaderboard`;
      try {
        const response = await axios.get(endpoint);
        setData(response.data);
        setError(null);
        setIsLoading(false);
      } catch (error) {
        console.error("Error fetching leaderboard data:", error);
        setError(error);
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  if (isLoading) {
    return <Loading />;
  }

  if (error) {
    return <div className="text-red-500 text-center py-4">{error.message}</div>;
  }

  if (!data) {
    return <div className="text-center py-4">Loading...</div>;
  }

  const { players, modes, regions, mode, region } = data;

  const filteredPlayers = players.filter((player) =>
    player.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = filteredPlayers.slice(indexOfFirstItem, indexOfLastItem);

  const paginate = (pageNumber) => setCurrentPage(pageNumber);

  return (
    <div className="container mx-auto px-4 py-8 bg-gray-900 text-white min-h-screen">
      <h1 className="text-3xl font-bold mb-4">
        Top 500 {region} - {mode}
      </h1>
      <input
        type="text"
        placeholder="Search"
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        className="border border-gray-700 bg-gray-800 rounded-md px-4 py-2 mb-4 w-full focus:outline-none focus:ring-2 focus:ring-purple"
      />
      <table className="table-auto w-full bg-gray-800">
        <thead>
          <tr className="bg-gray-700">
            <th className="px-4 py-2">Rank</th>
            <th className="px-4 py-2">Name</th>
            <th className="px-4 py-2">Splashtag</th>
            <th className="px-4 py-2">X Power</th>
            <th className="px-4 py-2">Weapon ID</th>
            <th className="px-4 py-2">Byname</th>
            <th className="px-4 py-2">Text Color</th>
          </tr>
        </thead>
        <tbody>
          {currentItems.map((player) => (
            <tr key={player.player_id} className="border-b border-gray-700">
              <td className="px-4 py-2">{player.rank}</td>
              <td className="px-4 py-2">{player.name}</td>
              <td className="px-4 py-2">{player.splashtag}</td>
              <td className="px-4 py-2">{player.x_power}</td>
              <td className="px-4 py-2">{player.weapon_id}</td>
              <td className="px-4 py-2">{player.byname}</td>
              <td className="px-4 py-2">{player.text_color}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex justify-center mt-4">
        {Array.from(
          { length: Math.ceil(filteredPlayers.length / itemsPerPage) },
          (_, i) => (
            <button
              key={i}
              onClick={() => paginate(i + 1)}
              className={`mx-1 px-4 py-2 rounded-md ${
                currentPage === i + 1 ? "bg-purple text-white" : "bg-gray-700"
              }`}
            >
              {i + 1}
            </button>
          )
        )}
      </div>
    </div>
  );
};

export default Top500;
