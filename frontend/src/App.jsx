import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { FaUpload, FaFileDownload, FaTimes, FaSync, FaSearch, FaMapMarkerAlt, FaKeyboard, FaEnvelope } from "react-icons/fa";
import API_BASE_URL from "./config";
import "./App.css";

const App = () => {
  const [file, setFile] = useState(null);
  const [keyword, setKeyword] = useState("");
  const [email, setEmail] = useState("");
  const [location, setLocation] = useState("");
  const [taskId, setTaskId] = useState(null);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [searchComplete, setSearchComplete] = useState(false);

  const [countries, setCountries] = useState([]);
  const [selectedCountry, setSelectedCountry] = useState("");
  const [cities, setCities] = useState([]);
  const [selectedCity, setSelectedCity] = useState("");

  const [loadingCountries, setLoadingCountries] = useState(true);
  const [loadingCities, setLoadingCities] = useState(false);
  const [error, setError] = useState(null);

  const intervalRef = useRef(null);
  const fileInputRef = useRef(null);

  const [countrySearch, setCountrySearch] = useState("");
  const [citySearch, setCitySearch] = useState("");

  // Add these new state variables
  const [searchType, setSearchType] = useState("file"); // "file" or "location"
  const [radiusKm, setRadiusKm] = useState(5);

  axios.defaults.baseURL = API_BASE_URL;

  // Fetch countries (JSON filenames from backend)
  useEffect(() => {
    const fetchCountries = async () => {
      try {
        const response = await axios.get("/countries");
        console.log("Countries API Response:", response.data);

        if (response.data?.countries) {
          setCountries(response.data.countries);
        } else {
          console.error("Unexpected API response:", response.data);
          setCountries([]); // Prevent crash
        }
      } catch (err) {
        console.error("Error fetching countries:", err.message);
        setCountries([]); // Prevent crash
      }
    };

    fetchCountries();
  }, []);

  // Handle country selection
  const handleCountryChange = async (e) => {
    const country = e.target.value;
    setSelectedCountry(country);
    setCities([]); // Reset cities


    if (!country) return;

    try {
      const response = await axios.get(`/cities/${encodeURIComponent(country)}`);
      console.log("Cities API Response:", response.data);

      if (response.data?.cities) {
        setCities(response.data.cities);
      } else {
        console.error("Unexpected API response:", response.data);
        setCities([]); // Prevent crash
      }
    } catch (err) {
      console.error("Error fetching cities:", err.message);
      setCities([]); // Prevent crash
    }
  };

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    // Common validation for both search types
    if (!keyword || !email) {
      alert("Please enter keyword and email.");
      return;
    }

    // Different validation and submission logic based on search type
    if (searchType === "file") {
      const file = fileInputRef.current.files[0];
      if (!file) {
        alert("Please upload a CSV file.");
        return;
      }

      const formData = new FormData();
      formData.append("file", file);
      formData.append("keyword", keyword);
      formData.append("email", email);
      formData.append("radius_km", String(radiusKm));

      try {
        const response = await axios.post("/upload/", formData);
        setTaskId(response.data.task_id);
        setIsRunning(true);
        setSearchComplete(false);
      } catch (error) {
        console.error("Error starting the scraping process", error);
      }
    } else { // location-based search
      if (!selectedCountry || !selectedCity) {
        alert("Please select both country and city.");
        return;
      }

      const formData = new FormData();
      formData.append("keyword", keyword);
      formData.append("email", email);
      formData.append("country", selectedCountry);
      formData.append("city", selectedCity);
      formData.append("radius_km", String(radiusKm));

      try {
        // API call for location-based search
        const response = await axios.post("/search-by-location/", formData);
        setTaskId(response.data.task_id);
        setIsRunning(true);
        setSearchComplete(false);
      } catch (error) {
        console.error("Error starting the location-based search", error);
      }
    }
  };

  // Add this useEffect
  useEffect(() => {
    function handleClickOutside(event) {
      const countryDropdown = document.getElementById("countryDropdown");
      const cityDropdown = document.getElementById("cityDropdown");

      if (countryDropdown && !event.target.closest('.custom-select')) {
        countryDropdown.classList.remove("show");
      }

      if (cityDropdown && !event.target.closest('.custom-select')) {
        cityDropdown.classList.remove("show");
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  useEffect(() => {
    if (taskId && isRunning) {
      intervalRef.current = setInterval(async () => {
        try {
          const response = await axios.get(`/progress/${taskId}`);

          if (response.data.progress !== undefined) {
            setProgress(response.data.progress);
          }
          if (response.data.results) {
            setResults(response.data.results);
          }
          if (!response.data.running) {
            setIsRunning(false);
            setSearchComplete(true);
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
        } catch (error) {
          console.error("Error fetching progress", error);
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      }, 2000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [taskId, isRunning]);

  const handleCancel = async () => {
    if (taskId) {
      try {
        await axios.post(`/cancel/${taskId}`);

        // Stop progress polling
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }

        // Reset state
        setTaskId(null);
        setIsRunning(false);
        setProgress(0);
        setSearchComplete(true);

        console.log(`Task ${taskId} canceled successfully.`);
      } catch (error) {
        console.error("Error canceling the task", error);
      }
    }
  };

  const handleDownload = async () => {
    if (taskId) {
      try {
        // Select the appropriate endpoint based on searchType
        const endpoint = searchType === "file"
          ? `/download/${taskId}`
          : `/download-search/${taskId}`;

        const response = await axios.get(endpoint, {
          responseType: 'blob'
        });

        const blob = new Blob([response.data], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;

        // Create different filename based on search type
        const filename = searchType === "file"
          ? `csv_file_results_${taskId}.csv`
          : `location_search_results_${taskId}.csv`;

        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
      } catch (error) {
        console.error("Error downloading CSV", error);
        alert("Failed to download CSV. Please try again.");
      }
    }
  };

  const handleResetForm = () => {
    setFile(null);
    setKeyword("");
    setSelectedCountry("");
    setSelectedCity("");
    setEmail("");
    setTaskId(null);
    setProgress(0);
    setResults([]);
    setIsRunning(false);
    setSearchComplete(false);
  };

  return (
    <div className="app-container">
      {/* Animated Background */}
      <div className="animated-background">
        <div className="gradient-overlay"></div>
        <div className="dot-pattern"></div>
      </div>

      {/* Content Container */}
      <div className="content-container">
        {/* Header */}
        <header className="app-header">
          <div className="header-container">
            <div className="logo-container">
              <div className="logo">
                <img src="https://dowellfileuploader.uxlivinglab.online/hr/logo-2-min-min.png" alt="logo" />
              </div>
              <h1 className="app-title">
                DoWell Samanta Scraper
              </h1>
            </div>
            <div className="app-badge">
              <span>Data Extraction Tool</span>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <div className="main-content">
          {/* Left Side: Form */}
          <div className="form-container">
            {/* Gradient Border */}
            <div className="gradient-border"></div>

            <form onSubmit={handleSubmit} className="scraper-form">
              {/* Search Type Selection */}
              <div className="search-type-selection">
                <div className="radio-group">
                  <label className={`radio-label ${searchType === "file" ? "selected" : ""}`}>
                    <input
                      type="radio"
                      name="searchType"
                      value="file"
                      checked={searchType === "file"}
                      onChange={() => setSearchType("file")}
                      className="radio-input"
                    />
                    By CSV
                  </label>
                  <label className={`radio-label ${searchType === "location" ? "selected" : ""}`}>
                    <input
                      type="radio"
                      name="searchType"
                      value="location"
                      checked={searchType === "location"}
                      onChange={() => setSearchType("location")}
                      className="radio-input"
                    />
                    By Location
                  </label>
                </div>
              </div>

              {/* File Upload - Only shown when file search type is selected */}
              {searchType === "file" && (
                <div className="file-upload">
                  <input
                    type="file"
                    accept=".csv"
                    onChange={handleFileChange}
                    ref={fileInputRef}
                    id="file-upload"
                    className="hidden-input"
                  />
                  <label
                    htmlFor="file-upload"
                    className="upload-button"
                  >
                    <FaUpload className="button-icon" />
                    Choose CSV File
                  </label>
                  {file && (
                    <p className="file-name">
                      Selected: {file.name}
                    </p>
                  )}
                </div>
              )}

              {/* Email Input - Common for both search types */}
              <div className="input-container">
                <FaEnvelope className="input-icon" />
                <input
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="form-input"
                />
              </div>

              {/* Keyword Input - Common for both search types */}
              <div className="input-container">
                <FaKeyboard className="input-icon" />
                <input
                  type="text"
                  placeholder="Keyword"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  required
                  className="form-input"
                />
              </div>

              {/* Radius Slider - Common for both search types */}
              <div className="input-container">
                <label className="slider-label" style={{ width: '100%' }}>
                  Search radius: {radiusKm} km
                  <input
                    type="range"
                    min="1"
                    max="50"
                    step="1"
                    value={radiusKm}
                    onChange={(e) => setRadiusKm(Number(e.target.value))}
                    className="slider-input"
                    style={{ width: '100%' }}
                  />
                </label>
              </div>

              {/* Location Selection - Only shown when location search type is selected */}
              {searchType === "location" && (
                <>
                  <div className="input-container">
                    <FaMapMarkerAlt className="input-icon" />
                    <div className="custom-select">
                      <div className="select-selected" onClick={() => document.getElementById("countryDropdown").classList.toggle("show")}>
                        {selectedCountry || "Select a Country"}
                      </div>
                      <div id="countryDropdown" className="select-items">
                        <div className="search-container">
                          <input
                            type="text"
                            placeholder="Search country..."
                            value={countrySearch}
                            onChange={(e) => setCountrySearch(e.target.value)}
                            className="dropdown-search"
                            onClick={(e) => e.stopPropagation()}
                          />
                        </div>
                        {countries
                          .filter(country => country.toLowerCase().includes(countrySearch.toLowerCase()))
                          .map((country, index) => (
                            <div
                              key={index}
                              className={`select-option ${selectedCountry === country ? 'selected' : ''}`}
                              onClick={() => {
                                setSelectedCountry(country);
                                handleCountryChange({ target: { value: country } });
                                document.getElementById("countryDropdown").classList.remove("show");
                              }}
                            >
                              {country}
                            </div>
                          ))}
                      </div>
                      <select
                        value={selectedCountry}
                        onChange={handleCountryChange}
                        required={searchType === "location"}
                        className="hidden-select"
                      >
                        <option value="" disabled>Select a Country</option>
                        {countries.map((country, index) => (
                          <option key={index} value={country}>{country}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {selectedCountry && (
                    <div className="input-container">
                      <FaMapMarkerAlt className="input-icon" />
                      <div className="custom-select">
                        <div className="select-selected" onClick={() => document.getElementById("cityDropdown").classList.toggle("show")}>
                          {selectedCity || "Select a City"}
                        </div>
                        <div id="cityDropdown" className="select-items">
                          <div className="search-container">
                            <input
                              type="text"
                              placeholder="Search city..."
                              value={citySearch}
                              onChange={(e) => setCitySearch(e.target.value)}
                              className="dropdown-search"
                              onClick={(e) => e.stopPropagation()}
                            />
                          </div>
                          {cities
                            .filter(city => city.toLowerCase().includes(citySearch.toLowerCase()))
                            .map((city, index) => (
                              <div
                                key={index}
                                className={`select-option ${selectedCity === city ? 'selected' : ''}`}
                                onClick={() => {
                                  setSelectedCity(city);
                                  document.getElementById("cityDropdown").classList.remove("show");
                                }}
                              >
                                {city}
                              </div>
                            ))}
                        </div>
                        <select
                          value={selectedCity}
                          onChange={(e) => setSelectedCity(e.target.value)}
                          required={searchType === "location"}
                          className="hidden-select"
                        >
                          <option value="" disabled>Select a City</option>
                          {cities.map((city, index) => (
                            <option key={index} value={city}>{city}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isRunning}
                className={`submit-button ${isRunning ? 'disabled' : ''}`}
              >
                <FaSearch className="button-icon" />
                {isRunning ? "Searching..." : "Start Scraping"}
              </button>

              {/* Progress Indicator */}
              {isRunning && (
                <div className="progress-container">
                  <div className="progress-bar-container">
                    <div
                      className="progress-bar"
                      style={{ width: `${progress}%` }}
                    ></div>
                  </div>
                  <div className="progress-info">
                    <p className="progress-text">
                      Progress: {progress.toFixed(2)}%
                    </p>
                    <button
                      onClick={handleCancel}
                      disabled={!isRunning}
                      className="cancel-button"
                    >
                      <FaTimes className="button-icon-small" /> Cancel
                    </button>
                  </div>
                </div>
              )}

              {/* Reset Button */}
              {searchComplete && (
                <button
                  onClick={handleResetForm}
                  className="reset-button"
                >
                  <FaSync className="button-icon" /> Reset Form
                </button>
              )}
            </form>
          </div>

          {/* Right Side: Results */}
          <div className="results-container">
            {/* Gradient Border */}
            <div className="gradient-border"></div>

            {results.length > 0 ? (
              <div className="results-content">
                {/* Results Table */}
                <div className="results-table-container">
                  <table className="results-table">
                    <thead>
                      <tr>
                        {/* Dynamic headers based on search type */}
                        {searchType === "file" ? (
                          ['Postal Code', 'Name', 'Address', 'Phone', 'Website', 'Google Maps URL', 'City', 'Country'].map((header) => (
                            <th key={header} className="table-header">
                              {header}
                            </th>
                          ))
                        ) : (
                          ['Name', 'Address', 'Phone', 'Website', 'Google Maps URL', 'City', 'Country'].map((header) => (
                            <th key={header} className="table-header">
                              {header}
                            </th>
                          ))
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {results.map((row, index) => (
                        <tr key={index} className="table-row">
                          {/* Show postal code only for file-based search */}
                          {searchType === "file" && (
                            <td className="table-cell">{row["Postal Code"]}</td>
                          )}
                          <td className="table-cell">{row.Name}</td>
                          <td className="table-cell">{row.Address}</td>
                          <td className="table-cell">{row.Phone}</td>
                          <td className="table-cell">
                            {row.Website !== "Not Available" ? (
                              <a
                                href={row.Website}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="table-link"
                              >
                                {row.Website}
                              </a>
                            ) : (
                              <span className="not-available">Not Available</span>
                            )}
                          </td>
                          <td className="table-cell">
                            <a
                              href={row.URL}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="table-link"
                            >
                              Maps URL
                            </a>
                          </td>
                          <td className="table-cell">{row.City}</td>
                          <td className="table-cell">{row.Country}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {/* Download Button */}
                <button
                  onClick={handleDownload}
                  className="download-button"
                >
                  <FaFileDownload className="button-icon" /> Download as CSV
                </button>
              </div>
            ) : (
              <div className="empty-results">
                <FaSearch className="empty-icon" />
                <p className="empty-text">Your search results will appear here</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;