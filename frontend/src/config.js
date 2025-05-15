const API_BASE_URL =
  window.location.hostname === "localhost"
    ? "http://localhost:8080/"
    : "https://map.uxlivinglab.online/"; 

export default API_BASE_URL;
