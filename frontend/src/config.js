const API_BASE_URL =
  window.location.hostname === "localhost"
    ? "http://localhost:8000/"
    : "https://map.uxlivinglab.online/api"; 

export default API_BASE_URL;