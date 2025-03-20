import React, { useState, useEffect } from "react";
import axios from "axios";
import "./App.css"

const App = () => {
  const [file, setFile] = useState(null);
  const [keyword, setKeyword] = useState("");
  const [location, setLocation] = useState("");
  const [taskId, setTaskId] = useState(null);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState([]);
  const [isRunning, setIsRunning] = useState(false);

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!file || !keyword || !location) {
      alert("Please fill in all fields and upload a file.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("keyword", keyword);
    formData.append("location", location);

    try {
      const response = await axios.post("http://localhost:8000/upload/", formData);
      setTaskId(response.data.task_id);
      setIsRunning(true);
    } catch (error) {
      console.error("Error starting the scraping process", error);
    }
  };

  useEffect(() => {
    if (taskId && isRunning) {
      const interval = setInterval(async () => {
        try {
          const response = await axios.get(`http://localhost:8000/progress/${taskId}`);
          setProgress(response.data.progress);
          if (response.data.results) {
            setResults(response.data.results);
          }
          if (!response.data.running) {
            setIsRunning(false);
            clearInterval(interval);
          }
        } catch (error) {
          console.error("Error fetching progress", error);
        }
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [taskId, isRunning]);

  const handleCancel = async () => {
    if (taskId) {
      await axios.post(`http://localhost:8000/cancel/${taskId}`);
      setIsRunning(false);
    }
  };

  const handleDownload = async () => {
    if (taskId) {
      window.location.href = `http://localhost:8000/download/${taskId}`;
    }
  };

  return (
    <div className="container">
    <div style={{ maxWidth: "600px", margin: "auto", textAlign: "center", padding: "20px" }}>
      <h1>Google Maps Scraper</h1>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        <input type="file" accept=".csv" onChange={handleFileChange} required />
        <input type="text" placeholder="Keyword" value={keyword} onChange={(e) => setKeyword(e.target.value)} required />
        <input type="text" placeholder="Location" value={location} onChange={(e) => setLocation(e.target.value)} required />
        <button type="submit" disabled={isRunning}>Start Scraping</button>
      </form>
      {isRunning && (
        <>
          <div style={{ width: "100%", backgroundColor: "#ccc", borderRadius: "5px", marginTop: "10px" }}>
            <div
              style={{
                width: `${progress}%`,
                height: "10px",
                backgroundColor: "#4caf50",
                borderRadius: "5px",
              }}
            ></div>
          </div>
          <p>Progress: {progress.toFixed(2)}%</p>
          <button onClick={handleCancel}>Cancel</button>
          <br></br>
          <br></br>
        </>
      )}
      {results.length > 0 && (
        <>
        <div className="table-container">
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
          <br></br>
          <button onClick={handleDownload}>Download CSV</button>
        </>
      )}
    </div>
    </div>
  );
};

export default App;