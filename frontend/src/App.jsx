import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ToastContainer, toast } from 'react-toastify';
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

  // Custom CSV Download function
  const downloadCSV = () => {
    const csvContent = "data:text/csv;charset=utf-8," 
      + results.map(e => Object.values(e).join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "search-results.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-white flex">
      {/* Sidebar */}
      <div className="w-80 bg-neutral-900 p-6 border-r border-neutral-800 flex flex-col">
        <div className="flex items-center mb-8">
          <MapPin className="w-8 h-8 mr-3 text-emerald-500" />
          <h1 className="text-2xl font-bold">MapSearch</h1>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="file-upload" className="block text-sm text-neutral-400 mb-2">
              Upload CSV with Postal Codes
            </label>
            <div className="flex items-center space-x-3">
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
                className="flex-grow bg-neutral-800 px-4 py-2 rounded-lg cursor-pointer hover:bg-neutral-700 transition"
              >
                {file ? file.name : 'Choose File'}
              </label>
              <Upload className="w-6 h-6 text-emerald-500" />
            </div>
            <p className="text-xs text-neutral-500 mt-1">CSV containing postal codes</p>
          </div>

          <div>
            <label htmlFor="keyword" className="block text-sm text-neutral-400 mb-2">
              Keyword
            </label>
            <input 
              type="text"
              id="keyword"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="e.g., Restaurants"
              disabled={isLoading}
              className="w-full bg-neutral-800 px-4 py-2 rounded-lg focus:ring-2 focus:ring-emerald-500 outline-none"
            />
          </div>

          <div>
            <label htmlFor="location" className="block text-sm text-neutral-400 mb-2">
              Location
            </label>
            <input 
              type="text"
              id="location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g., New York"
              disabled={isLoading}
              className="w-full bg-neutral-800 px-4 py-2 rounded-lg focus:ring-2 focus:ring-emerald-500 outline-none"
            />
          </div>

          <div className="flex space-x-4">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              type="submit"
              disabled={isLoading}
              className="flex-grow bg-emerald-600 text-white py-3 rounded-lg hover:bg-emerald-700 transition flex items-center justify-center"
            >
              <Search className="mr-2" /> Search
            </motion.button>
            
            {isLoading && (
              <motion.button 
                type="button" 
                onClick={cancelSearch}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="bg-red-600 text-white px-4 py-3 rounded-lg hover:bg-red-700 transition flex items-center"
              >
                <X className="mr-2" /> Cancel
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
                <div className="w-full bg-neutral-800 rounded-full h-2.5">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${progress}%` }}
                    transition={{ duration: 0.5 }}
                    className="bg-emerald-600 h-2.5 rounded-full"
                  ></motion.div>
                </div>
                <p className="text-center text-sm text-neutral-400 mt-2">
                  {progress}% Complete
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </form>
      </div>

      {/* Results Area */}
      <div className="flex-grow bg-neutral-900 p-8 overflow-y-auto">
        <AnimatePresence>
          {results.length > 0 && (
            <motion.div 
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-3xl font-bold text-emerald-500">
                  Search Results
                </h2>
                <button 
                  onClick={downloadCSV}
                  className="flex items-center px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition"
                >
                  <Download className="mr-2 w-5 h-5" /> Download CSV
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full bg-neutral-800 rounded-lg overflow-hidden">
                  <thead className="bg-neutral-700">
                    <tr>
                      {['Name', 'Address', 'Phone', 'Website', 'Rating', 'Reviews', 'Postal Code'].map((header) => (
                        <th key={header} className="px-4 py-3 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">
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
                          className="border-b border-neutral-700 hover:bg-neutral-700 transition"
                        >
                          <td className="px-4 py-3 text-white">{result.name}</td>
                          <td className="px-4 py-3 text-neutral-300">{result.address}</td>
                          <td className="px-4 py-3 text-neutral-300">{result.phone}</td>
                          <td className="px-4 py-3">
                            {result.website && (
                              <a 
                                href={result.website} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="text-emerald-500 hover:underline"
                              >
                                {result.website}
                              </a>
                            )}
                          </td>
                          <td className="px-4 py-3 text-white">{result.rating}</td>
                          <td className="px-4 py-3 text-neutral-300">{result.reviews}</td>
                          <td className="px-4 py-3 text-neutral-300">{result.postal_code}</td>
                        </motion.tr>
                      ))}
                    </AnimatePresence>
                  </tbody>
                </table>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <ToastContainer 
        position="bottom-right" 
        theme="dark"
        hideProgressBar={false}
        closeOnClick
        pauseOnHover
      />
    </div>
  );
}

export default App;