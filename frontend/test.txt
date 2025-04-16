import React, { useState, useEffect } from "react";
import axios from "axios";
import "./App.css";
import API_BASE_URL from "./config";
import { FaUpload } from "react-icons/fa";

const App = () => {
  const [file, setFile] = useState(null);
  const [keyword, setKeyword] = useState("");
  const [location, setLocation] = useState("");
  const [taskId, setTaskId] = useState(null);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [searchComplete, setSearchComplete] = useState(false);

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!file || !keyword || !location) {
      alert("Please fill in all fields and upload a file.");
      return;
    }

    axios.defaults.baseURL = API_BASE_URL;

    const formData = new FormData();
    formData.append("file", file);
    formData.append("keyword", keyword);
    formData.append("location", location);

    try {
      const response = await axios.post("/upload/", formData);
      setTaskId(response.data.task_id);
      setIsRunning(true);
      setSearchComplete(false);
    } catch (error) {
      console.error("Error starting the scraping process", error);
    }
  };

  useEffect(() => {
    if (taskId && isRunning) {
      const interval = setInterval(async () => {
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
            clearInterval(interval);
          }
        } catch (error) {
          console.error("Error fetching progress", error);
          clearInterval(interval);
        }
      }, 2000);

      return () => clearInterval(interval);
    }
  }, [taskId, isRunning]);

  const handleCancel = async () => {
    if (taskId) {
      await axios.post(`/cancel/${taskId}`);
      setIsRunning(false);
    }
  };

  const handleDownload = async () => {
    if (taskId) {
      window.location.href = `/download/${taskId}`;
    }
  };

  const handleResetForm = () => {
    setFile(null);
    setKeyword("");
    setLocation("");
    setTaskId(null);
    setProgress(0);
    setResults([]);
    setIsRunning(false);
    setSearchComplete(false);
  };

  return (
    <div className="app-container">
      <div className="header">
        <h1>Samanta Scraper</h1>
      </div>

      <div className="main-content">
        {/* Left Side: Form */}
        <div className="form-container">
          <form onSubmit={handleSubmit} className="form">
            <div className="file-input-container">
              <input
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                required
                id="file-upload"
                className="file-input"
              />
              <label htmlFor="file-upload" className="file-label">
                <FaUpload className="upload-icon" /> Choose File
              </label>
              {file && <p className="file-name">{file.name}</p>}
            </div>
            <input type="text" placeholder="Keyword" value={keyword} onChange={(e) => setKeyword(e.target.value)} required />
            <input type="text" placeholder="Location" value={location} onChange={(e) => setLocation(e.target.value)} required />
            <button type="submit" disabled={isRunning} className="start-btn">
              {isRunning ? "Searching..." : "Start Scraping"}
            </button>
          </form>

          {isRunning && (
            <div className="progress-container">
              <div className="progress-bar" style={{ width: `${progress}%` }}></div>
              <p>Progress: {progress.toFixed(2)}%</p>
              <button onClick={handleCancel} className="cancel-btn">Cancel</button>
            </div>
          )}

          {searchComplete && (
            <button onClick={handleResetForm} className="reset-btn">Reset Form</button>
          )}
        </div>

        {/* Right Side: Results Table */}
        <div className="results-container">
          {results.length > 0 && (
            <>
              <div className="results-table">
                <table>
                  <thead>
                    <tr>
                      <th>Postal Code</th>
                      <th>Name</th>
                      <th>Address</th>
                      <th>Phone</th>
                      <th>Website</th>
                      <th>Google Maps URL</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((row, index) => (
                      <tr key={index}>
                        <td>{row["Postal Code"]}</td>
                        <td>{row.Name}</td>
                        <td>{row.Address}</td>
                        <td>{row.Phone}</td>
                        <td>
                          {row.Website !== "Not Available" ? (
                            <a href={row.Website} target="_blank" rel="noopener noreferrer">
                              {row.Website}
                            </a>
                          ) : (
                            "Not Available"
                          )}
                        </td>
                        <td>
                          <a href={row.URL} target="_blank" rel="noopener noreferrer">
                            Google Maps
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <button onClick={handleDownload} className="download-btn">Download CSV</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;
