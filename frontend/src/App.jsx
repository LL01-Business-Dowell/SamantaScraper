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
    <div className="min-h-screen bg-[#121420] text-gray-100 flex flex-col overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0 bg-[#121420] z-0">
        <div className="absolute top-0 left-0 w-full h-full opacity-20 bg-gradient-to-br from-purple-900/10 via-indigo-900/10 to-blue-900/10 animate-gradient-slow"></div>
        <div className="absolute inset-0 bg-dot-white/[0.2] pointer-events-none"></div>
      </div>

      {/* Content Container */}
      <div className="relative z-10 flex flex-col flex-grow">
        {/* Header */}
        <header className="px-6 py-4 border-b border-gray-800/50 backdrop-blur-sm bg-[#121420]/80">
          <div className="container mx-auto flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-full flex items-center justify-center">
                {/* <FaSearch className="text-white text-xl" /> */}
                <img src="https://dowellfileuploader.uxlivinglab.online/hr/logo-2-min-min.png" alt="logo" />
              </div>
              <h1 className="text-2xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-indigo-400">
                DoWell Samanta Scraper
              </h1>
            </div>
            <div className="bg-gray-800/50 px-4 py-2 rounded-full">
              <span className="text-sm font-medium text-gray-300">Data Extraction Tool</span>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <div className="container mx-auto px-6 py-10 grid md:grid-cols-2 gap-10 flex-grow">
          {/* Left Side: Form */}
          <div className="bg-[#1A1E2E] rounded-3xl shadow-2xl border border-gray-800/50 p-8 space-y-6 relative overflow-hidden">
            {/* Gradient Border */}
            <div className="absolute inset-0 bg-gradient-to-br from-purple-900/20 via-indigo-900/20 to-blue-900/20 opacity-50 -z-10"></div>
            
            <form onSubmit={handleSubmit} className="relative z-10 space-y-6">
              {/* File Upload */}
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
                  className="flex items-center justify-center bg-gradient-to-r from-purple-600 to-indigo-700 text-white py-3 px-6 rounded-xl hover:scale-[1.02] transition-transform duration-300 ease-in-out shadow-lg hover:shadow-xl"
                >
                  <FaUpload className="mr-3 text-lg" /> 
                  Choose CSV File
                </label>
                {file && (
                  <p className="text-sm text-gray-400 mt-3 truncate bg-gray-800 px-3 py-2 rounded-lg">
                    Selected: {file.name}
                  </p>
                )}
              </div>

              {/* Keyword Input */}
              <div className="relative">
                <FaKeyboard className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500" />
                <input 
                  type="text" 
                  placeholder="Keyword" 
                  value={keyword} 
                  onChange={(e) => setKeyword(e.target.value)} 
                  required 
                  className="w-full pl-10 px-3 py-3 bg-gray-800 border border-gray-700 text-gray-100 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 transition duration-300"
                />
              </div>

              {/* Location Input */}
              <div className="relative">
                <FaMapMarkerAlt className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500" />
                <input 
                  type="text" 
                  placeholder="Location" 
                  value={location} 
                  onChange={(e) => setLocation(e.target.value)} 
                  required 
                  className="w-full pl-10 px-3 py-3 bg-gray-800 border border-gray-700 text-gray-100 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 transition duration-300"
                />
              </div>

              {/* Submit Button */}
              <button 
                type="submit" 
                disabled={isRunning} 
                className={`w-full py-3 rounded-xl transition-all duration-300 flex items-center justify-center ${
                  isRunning 
                    ? 'bg-gray-700 cursor-not-allowed' 
                    : 'bg-gradient-to-r from-purple-600 to-indigo-700 text-white hover:from-purple-700 hover:to-indigo-800 shadow-lg hover:shadow-xl'
                }`}
              >
                <FaSearch className="mr-3" />
                {isRunning ? "Searching..." : "Start Scraping"}
              </button>

              {/* Progress Indicator */}
              {isRunning && (
                <div className="mt-6">
                  <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                    <div 
                      className="bg-gradient-to-r from-purple-600 to-indigo-700 h-full rounded-full transition-all duration-500" 
                      style={{ width: `${progress}%` }}
                    ></div>
                  </div>
                  <div className="flex justify-between items-center mt-3">
                    <p className="text-sm text-gray-400 font-medium">
                      Progress: {progress.toFixed(2)}%
                    </p>
                    <button 
                      onClick={handleCancel} 
                      className="text-red-500 hover:text-red-400 flex items-center font-medium"
                    >
                      <FaTimes className="mr-2" /> Cancel
                    </button>
                  </div>
                </div>
              )}

              {/* Reset Button */}
              {searchComplete && (
                <button 
                  onClick={handleResetForm} 
                  className="w-full mt-6 py-3 bg-gray-800 text-gray-300 rounded-xl hover:bg-gray-700 flex items-center justify-center transition-all"
                >
                  <FaSync className="mr-3" /> Reset Form
                </button>
              )}
            </form>
          </div>

          {/* Right Side: Results */}
          <div className="bg-[#1A1E2E] rounded-3xl shadow-2xl border border-gray-800/50 p-8 relative overflow-hidden">
            {/* Gradient Border */}
            <div className="absolute inset-0 bg-gradient-to-br from-purple-900/20 via-indigo-900/20 to-blue-900/20 opacity-50 -z-10"></div>

            {results.length > 0 ? (
              <div className="space-y-6">
                {/* Results Table */}
                <div className="overflow-x-auto max-h-[500px] rounded-xl border border-gray-700">
                  <table className="w-full">
                    <thead className="bg-[#252B3E] sticky top-0">
                      <tr>
                        {['Postal Code', 'Name', 'Address', 'Phone', 'Website', 'Google Maps URL'].map((header) => (
                          <th key={header} className="px-4 py-3 text-left text-xs font-bold text-gray-400 uppercase tracking-wider border-b border-gray-700">
                            {header}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                      {results.map((row, index) => (
                        <tr key={index} className="hover:bg-gray-800/50 transition-colors">
                          <td className="px-4 py-3 text-gray-300">{row["Postal Code"]}</td>
                          <td className="px-4 py-3 text-gray-300">{row.Name}</td>
                          <td className="px-4 py-3 text-gray-300">{row.Address}</td>
                          <td className="px-4 py-3 text-gray-300">{row.Phone}</td>
                          <td className="px-4 py-3">
                            {row.Website !== "Not Available" ? (
                              <a 
                                href={row.Website} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="text-purple-400 hover:text-purple-300 hover:underline transition"
                              >
                                {row.Website}
                              </a>
                            ) : (
                              <span className="text-gray-500">Not Available</span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <a 
                              href={row.URL} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="text-purple-400 hover:text-purple-300 hover:underline transition"
                            >
                              Google Maps
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Download Button */}
                <button 
                  onClick={handleDownload} 
                  className="w-full py-3 bg-gradient-to-r from-purple-600 to-indigo-700 text-white rounded-xl hover:from-purple-700 hover:to-indigo-800 flex items-center justify-center transition-all shadow-lg hover:shadow-xl"
                >
                  <FaFileDownload className="mr-3 text-lg" /> Download CSV
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
                <FaSearch className="text-6xl mb-4 opacity-20" />
                <p className="text-xl font-light">Your search results will appear here</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;