import React, { useState, useEffect } from "react";
import axios from "axios";
import { FaUpload, FaFileDownload, FaTimes, FaSync, FaSearch, FaMapMarkerAlt, FaKeyboard } from "react-icons/fa";
import API_BASE_URL from "./config";

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
      try {
        const response = await axios.get(`/download/${taskId}`, {
          responseType: 'blob'
        });

        const blob = new Blob([response.data], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `results_${taskId}.csv`;
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
    setLocation("");
    setTaskId(null);
    setProgress(0);
    setResults([]);
    setIsRunning(false);
    setSearchComplete(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-blue-100 flex flex-col">
      <header className="bg-gradient-to-r from-blue-600 to-indigo-700 text-white py-6 shadow-lg">
        <div className="container mx-auto px-4 flex items-center justify-between">
          <h1 className="text-3xl font-extrabold tracking-tight">DoWell Samanta Scraper</h1>
          <div className="bg-white/20 px-4 py-2 rounded-full">
            <span className="text-sm font-medium">Data Extraction Tool</span>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-10 grid md:grid-cols-2 gap-10">
        {/* Left Side: Form */}
        <div className="bg-white rounded-2xl shadow-2xl p-8 border-2 border-blue-100 transform transition-all hover:scale-[1.02]">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="flex flex-col">
              <input
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                required
                id="file-upload"
                className="hidden"
              />
              <label 
                htmlFor="file-upload" 
                className="flex items-center justify-center bg-gradient-to-r from-blue-500 to-indigo-600 text-white py-3 px-6 rounded-lg hover:from-blue-600 hover:to-indigo-700 transition-all cursor-pointer shadow-md"
              >
                <FaUpload className="mr-3 text-lg" /> 
                Choose CSV File
              </label>
              {file && (
                <p className="text-sm text-gray-600 mt-3 truncate bg-gray-100 px-3 py-2 rounded">
                  Selected: {file.name}
                </p>
              )}
            </div>

            <div className="relative">
              <FaKeyboard className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input 
                type="text" 
                placeholder="Keyword" 
                value={keyword} 
                onChange={(e) => setKeyword(e.target.value)} 
                required 
                className="w-full pl-10 px-3 py-3 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div className="relative">
              <FaMapMarkerAlt className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input 
                type="text" 
                placeholder="Location" 
                value={location} 
                onChange={(e) => setLocation(e.target.value)} 
                required 
                className="w-full pl-10 px-3 py-3 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <button 
              type="submit" 
              disabled={isRunning} 
              className={`w-full py-3 rounded-lg transition-all duration-300 flex items-center justify-center ${
                isRunning 
                  ? 'bg-gray-400 cursor-not-allowed' 
                  : 'bg-gradient-to-r from-green-500 to-teal-600 text-white hover:from-green-600 hover:to-teal-700 shadow-lg hover:shadow-xl'
              }`}
            >
              <FaSearch className="mr-3" />
              {isRunning ? "Searching..." : "Start Scraping"}
            </button>

            {isRunning && (
              <div className="mt-6">
                <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                  <div 
                    className="bg-gradient-to-r from-blue-500 to-indigo-600 h-full rounded-full transition-all duration-500" 
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
                <div className="flex justify-between items-center mt-3">
                  <p className="text-sm text-gray-600 font-medium">
                    Progress: {progress.toFixed(2)}%
                  </p>
                  <button 
                    onClick={handleCancel} 
                    className="text-red-500 hover:text-red-600 flex items-center font-medium"
                  >
                    <FaTimes className="mr-2" /> Cancel
                  </button>
                </div>
              </div>
            )}

            {searchComplete && (
              <button 
                onClick={handleResetForm} 
                className="w-full mt-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 flex items-center justify-center transition-all"
              >
                <FaSync className="mr-3" /> Reset Form
              </button>
            )}
          </form>
        </div>

        {/* Right Side: Results Table */}
        <div className="bg-white rounded-2xl shadow-2xl p-8 border-2 border-blue-100 transform transition-all hover:scale-[1.02]">
          {results.length > 0 ? (
            <>
              <div className="overflow-x-auto max-h-[500px] rounded-lg border border-gray-200">
                <table className="w-full">
                  <thead className="bg-gradient-to-r from-blue-50 to-blue-100 sticky top-0">
                    <tr>
                      {['Postal Code', 'Name', 'Address', 'Phone', 'Website', 'Google Maps URL'].map((header) => (
                        <th key={header} className="px-4 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider border-b">
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {results.map((row, index) => (
                      <tr key={index} className="hover:bg-blue-50 transition-colors">
                        <td className="px-4 py-3">{row["Postal Code"]}</td>
                        <td className="px-4 py-3">{row.Name}</td>
                        <td className="px-4 py-3">{row.Address}</td>
                        <td className="px-4 py-3">{row.Phone}</td>
                        <td className="px-4 py-3">
                          {row.Website !== "Not Available" ? (
                            <a 
                              href={row.Website} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:text-blue-800 hover:underline transition"
                            >
                              {row.Website}
                            </a>
                          ) : (
                            "Not Available"
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <a 
                            href={row.URL} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 hover:underline transition"
                          >
                            Google Maps
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <button 
                onClick={handleDownload} 
                className="mt-6 w-full py-3 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-lg hover:from-blue-600 hover:to-indigo-700 flex items-center justify-center transition-all shadow-lg hover:shadow-xl"
              >
                <FaFileDownload className="mr-3 text-lg" /> Download CSV
              </button>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center text-gray-400">
              <FaSearch className="text-6xl mb-4 opacity-30" />
              <p className="text-xl font-light">Your search results will appear here</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;