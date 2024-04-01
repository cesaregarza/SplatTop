import React, { useEffect, useState } from 'react';
import axios from 'axios';

const Top500 = () => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null); // Added error state
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;

  useEffect(() => {
    const fetchData = async () => {
      console.log(process.env);
      const apiUrl = process.env.REACT_APP_API_URL || '';
      const endpoint = `${apiUrl}/api/leaderboard`;
      try {
        const response = await axios.get(endpoint);
        setData(response.data);
        setError(null); // Reset error state on successful response
      } catch (error) {
        console.error('Error fetching leaderboard data:', error);
        setError(error); // Set error state
      }
    };
  
    fetchData();
  }, []);

  if (error) {
    return <div>Error loading data: {error.message}</div>; // Display error message
  }

  if (!data) {
    return <div>Loading...</div>;
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
    <div>
      <h1>Top 500 {region} - {mode}</h1>
      <input
        type="text"
        placeholder="Search"
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
      />
      <table>
        <thead>
          <tr>
            <th>Rank</th>
            <th>Name</th>
            <th>Splashtag</th>
            <th>X Power</th>
            <th>Weapon ID</th>
            <th>Byname</th>
            <th>Text Color</th>
          </tr>
        </thead>
        <tbody>
          {currentItems.map((player) => (
            <tr key={player.player_id}>
              <td>{player.rank}</td>
              <td>{player.name}</td>
              <td>{player.splashtag}</td>
              <td>{player.x_power}</td>
              <td>{player.weapon_id}</td>
              <td>{player.byname}</td>
              <td>{player.text_color}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div>
        {Array.from({ length: Math.ceil(filteredPlayers.length / itemsPerPage) }, (_, i) => (
          <button key={i} onClick={() => paginate(i + 1)}>
            {i + 1}
          </button>
        ))}
      </div>
    </div>
  );
};

export default Top500;