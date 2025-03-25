import { useState, useEffect } from 'react';
import { ToastContainer, toast } from 'react-toastify';
import { CSVLink } from 'react-csv';
import axios from 'axios';
import 'react-toastify/dist/ReactToastify.css';
import './App.css';

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

  return (
    <div className="app-container">
      <header>
        <h1>Google Maps Search Tool</h1>
      </header>

      <main>
        <section className="search-section">
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="file-upload">Upload CSV with Postal Codes</label>
              <input
                type="file"
                id="file-upload"
                accept=".csv"
                onChange={handleFileChange}
                disabled={isLoading}
              />
              <small>File must be a CSV containing postal codes</small>
            </div>

            <div className="form-group">
              <label htmlFor="keyword">Keyword</label>
              <input
                type="text"
                id="keyword"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="e.g., Restaurants"
                disabled={isLoading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="location">Location</label>
              <input
                type="text"
                id="location"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g., New York"
                disabled={isLoading}
              />
            </div>

            <div className="button-group">
              <button 
                type="submit" 
                className="search-button"
                disabled={isLoading}
              >
                Search
              </button>
              
              {isLoading && (
                <button 
                  type="button" 
                  className="cancel-button"
                  onClick={cancelSearch}
                >
                  Cancel
                </button>
              )}
            </div>
          </form>

          {isLoading && (
            <div className="progress-container">
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
              <p className="progress-text">{progress}% Complete</p>
            </div>
          )}
        </section>

        <section className="results-section">
          <div className="results-header">
            <h2>Search Results</h2>
            {results.length > 0 && (
              <CSVLink 
                data={results}
                filename={'search-results.csv'}
                className="download-button"
              >
                Download CSV
              </CSVLink>
            )}
          </div>

          {results.length > 0 ? (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Address</th>
                    <th>Phone</th>
                    <th>Website</th>
                    <th>Rating</th>
                    <th>Reviews</th>
                    <th>Postal Code</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((result, index) => (
                    <tr key={index}>
                      <td>{result.name}</td>
                      <td>{result.address}</td>
                      <td>{result.phone}</td>
                      <td>
                        {result.website && (
                          <a href={result.website} target="_blank" rel="noopener noreferrer">
                            {result.website}
                          </a>
                        )}
                      </td>
                      <td>{result.rating}</td>
                      <td>{result.reviews}</td>
                      <td>{result.postal_code}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="no-results">No results to display</p>
          )}
        </section>
      </main>

      <ToastContainer position="bottom-right" />
    </div>
  );
}

export default App;