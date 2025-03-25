# Google Maps Scraper Web Application

This project provides a web application that allows users to search for businesses on Google Maps based on keywords, locations, and postal codes without using the paid Google Maps API. Instead, it uses Selenium with headless Chrome to perform searches and extract data.

## Features

- **React Frontend**: Modern, responsive UI built with React and Vite
- **FastAPI Backend**: Efficient API with background task processing
- **Dockerized Setup**: Easy deployment with Docker and docker-compose
- **CSV Upload**: Upload postal codes via CSV file
- **Progress Tracking**: Real-time progress updates during search
- **Cancelable Tasks**: Ability to cancel ongoing searches
- **Data Export**: Download search results as CSV

## Project Structure

```
project-root/
├── frontend/          # React frontend built with Vite
├── backend/           # FastAPI backend
├── docker-compose.yml # Docker Compose configuration
└── README.md          # This file
```

## Requirements

- Docker
- Docker Compose

## Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd google-maps-scraper
```

### 2. Start the application with Docker Compose

```bash
docker-compose up
```

This will:
- Build the frontend and backend Docker images
- Start both services
- Make the app available at http://localhost:3000

### 3. Using the application

1. Visit http://localhost:3000 in your browser
2. Upload a CSV file containing a column named 'postal_code'
3. Enter a keyword (e.g., "restaurants", "coffee shops", etc.)
4. Enter a location (e.g., "New York", "London", etc.)
5. Click "Search" and wait for the results
6. Download results as CSV using the "Download CSV" button

## CSV Format

The uploaded CSV file should have a column named 'postal_code' containing the postal codes you want to search.

Example:
```
postal_code
10001
10002
10003
```

## Development

### Frontend Development

The frontend is in the `frontend/` directory. To develop locally:

```bash
cd frontend
npm install
npm run dev
```

### Backend Development

The backend is in the `backend/` directory. To develop locally:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Technical Details

### Frontend

- Built with React and Vite
- Uses axios for API requests
- Styled with custom CSS for responsive design
- Uses react-csv for CSV export
- Uses react-toastify for notifications

### Backend

- Built with FastAPI
- Uses Selenium with headless Chrome for web scraping
- Background task processing for long-running searches
- In-memory task management

## Docker Configuration

- Frontend container: Node.js with Vite development server
- Backend container: Python with FastAPI, headless Chrome, and ChromeDriver
- Docker Compose for coordinating both services

## Limitations

- Google Maps may block your IP if you make too many requests in a short period
- The scraper is dependent on Google Maps HTML structure, which may change
- Limited to 20 results per postal code to avoid long execution times