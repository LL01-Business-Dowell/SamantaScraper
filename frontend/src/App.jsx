import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ToastContainer, toast } from 'react-toastify';
import { CSVLink } from 'react-csv';
import axios from 'axios';
import { 
  Upload, 
  Search, 
  MapPin, 
  X, 
  Download, 
  Loader2 
} from 'lucide-react';

import 'react-toastify/dist/ReactToastify.css';

function App() {
  const [file, setFile] = useState(null);
  const [keyword, setKeyword] = useState('');
  const [location, setLocation] = useState('');
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [taskId, setTaskId] = useState(null);

  axios.defaults.baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.type !== 'text/csv') {
      toast.error('Please upload a CSV file');
      return;
    }
    setFile(selectedFile);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!file) {
      toast.error('Please upload a CSV file');
      return;
    }
    
    if (!keyword.trim()) {
      toast.error('Please enter a keyword');
      return;
    }
    
    if (!location.trim()) {
      toast.error('Please enter a location');
      return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('keyword', keyword);
    formData.append('location', location);
    
    setIsLoading(true);
    setProgress(0);
    setResults([]);
    
    try {
      const response = await axios.post('/api/search', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      setTaskId(response.data.task_id);
      
      // Start polling for results
      const intervalId = setInterval(async () => {
        const statusResponse = await axios.get(`/api/status/${response.data.task_id}`);
        const { status, progress, results } = statusResponse.data;
        
        setProgress(progress);
        
        if (status === 'completed') {
          setResults(results);
          setIsLoading(false);
          clearInterval(intervalId);
          toast.success('Search completed successfully!');
        } else if (status === 'failed') {
          setIsLoading(false);
          clearInterval(intervalId);
          toast.error('Search failed. Please try again.');
        }
      }, 1000);
      
    } catch (error) {
      console.error('Error:', error);
      setIsLoading(false);
      toast.error('An error occurred. Please try again.');
    }
  };

  const cancelSearch = async () => {
    if (taskId) {
      try {
        await axios.delete(`/api/cancel/${taskId}`);
        setIsLoading(false);
        setProgress(0);
        toast.info('Search cancelled');
      } catch (error) {
        console.error('Error cancelling search:', error);
      }
    }
  };

  // Custom CSV Download Link to avoid prop-types dependency
  const CustomCSVLink = ({ data, filename, children, ...props }) => {
    const handleDownload = () => {
      const csvContent = "data:text/csv;charset=utf-8," 
        + data.map(e => Object.values(e).join(",")).join("\n");
      const encodedUri = encodeURI(csvContent);
      const link = document.createElement("a");
      link.setAttribute("href", encodedUri);
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    };

    return (
      <button 
        onClick={handleDownload} 
        className="flex items-center px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition"
        {...props}
      >
        {children}
      </button>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-blue-100 p-6 flex flex-col items-center">
      <motion.div 
        initial={{ opacity: 0, y: -50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-4xl bg-white shadow-2xl rounded-2xl overflow-hidden"
      >
        <header className="bg-blue-600 text-white p-6">
          <motion.h1 
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            className="text-3xl font-bold text-center flex items-center justify-center gap-3"
          >
            <MapPin className="w-10 h-10" />
            Google Maps Search Tool
          </motion.h1>
        </header>

        <div className="p-8">
          <motion.form 
            onSubmit={handleSubmit}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="space-y-6"
          >
            <div className="grid md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label htmlFor="file-upload" className="block text-sm font-medium text-gray-700">
                  Upload CSV with Postal Codes
                </label>
                <div className="flex items-center">
                  <input
                    type="file"
                    id="file-upload"
                    accept=".csv"
                    onChange={handleFileChange}
                    disabled={isLoading}
                    className="hidden"
                  />
                  <label 
                    htmlFor="file-upload" 
                    className="flex items-center px-4 py-2 bg-blue-500 text-white rounded-md cursor-pointer hover:bg-blue-600 transition"
                  >
                    <Upload className="mr-2 w-5 h-5" />
                    {file ? file.name : 'Choose File'}
                  </label>
                </div>
                <p className="text-xs text-gray-500 mt-1">CSV containing postal codes</p>
              </div>

              <div className="space-y-2">
                <label htmlFor="keyword" className="block text-sm font-medium text-gray-700">
                  Keyword
                </label>
                <input
                  type="text"
                  id="keyword"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  placeholder="e.g., Restaurants"
                  disabled={isLoading}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label htmlFor="location" className="block text-sm font-medium text-gray-700">
                Location
              </label>
              <input
                type="text"
                id="location"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g., New York"
                disabled={isLoading}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex space-x-4">
              <motion.button 
                type="submit" 
                disabled={isLoading}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="flex items-center justify-center px-6 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 disabled:opacity-50 transition"
              >
                <Search className="mr-2 w-5 h-5" />
                Search
              </motion.button>
              
              {isLoading && (
                <motion.button 
                  type="button" 
                  onClick={cancelSearch}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="flex items-center justify-center px-6 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 transition"
                >
                  <X className="mr-2 w-5 h-5" />
                  Cancel
                </motion.button>
              )}
            </div>

            <AnimatePresence>
              {isLoading && (
                <motion.div 
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mt-4 overflow-hidden"
                >
                  <div className="w-full bg-gray-200 rounded-full h-2.5">
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ width: `${progress}%` }}
                      transition={{ duration: 0.5 }}
                      className="bg-blue-600 h-2.5 rounded-full"
                    ></motion.div>
                  </div>
                  <p className="text-center text-sm text-gray-600 mt-2">
                    {progress}% Complete
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.form>

          <AnimatePresence>
            {results.length > 0 && (
              <motion.section 
                initial={{ opacity: 0, y: 50 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="mt-8"
              >
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-2xl font-semibold text-gray-800">Search Results</h2>
                  <CustomCSVLink 
                    data={results}
                    filename={'search-results.csv'}
                  >
                    <Download className="mr-2 w-5 h-5" />
                    Download CSV
                  </CustomCSVLink>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full bg-white shadow rounded-lg overflow-hidden">
                    <thead className="bg-blue-100">
                      <tr>
                        {['Name', 'Address', 'Phone', 'Website', 'Rating', 'Reviews', 'Postal Code'].map((header) => (
                          <th key={header} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            {header}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      <AnimatePresence>
                        {results.map((result, index) => (
                          <motion.tr 
                            key={index}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: index * 0.1 }}
                            className="border-b hover:bg-gray-50 transition"
                          >
                            <td className="px-4 py-3">{result.name}</td>
                            <td className="px-4 py-3">{result.address}</td>
                            <td className="px-4 py-3">{result.phone}</td>
                            <td className="px-4 py-3">
                              {result.website && (
                                <a 
                                  href={result.website} 
                                  target="_blank" 
                                  rel="noopener noreferrer"
                                  className="text-blue-600 hover:underline"
                                >
                                  {result.website}
                                </a>
                              )}
                            </td>
                            <td className="px-4 py-3">{result.rating}</td>
                            <td className="px-4 py-3">{result.reviews}</td>
                            <td className="px-4 py-3">{result.postal_code}</td>
                          </motion.tr>
                        ))}
                      </AnimatePresence>
                    </tbody>
                  </table>
                </div>
              </motion.section>
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      <ToastContainer 
        position="bottom-right" 
        theme="colored"
        hideProgressBar={false}
        closeOnClick
        pauseOnHover
      />
    </div>
  );
}

export default App;