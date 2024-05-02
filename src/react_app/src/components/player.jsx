import React, { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import axios from "axios";
import Loading from "./loading";
import XChart from "./player_components/xchart";

const PlayerPage = () => {
  const location = useLocation();
  const player_id = location.pathname.split("/")[2];
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [mode, setMode] = useState("Splat Zones");
  const [removeValuesNotInTop500, setRemoveValuesNotInTop500] = useState(true);

  const isDevelopment = process.env.NODE_ENV === "development";
  const apiUrl = isDevelopment
    ? "http://localhost:5000"
    : process.env.REACT_APP_API_URL || "";
  const endpoint = `${apiUrl}/player/${player_id}`;
};
