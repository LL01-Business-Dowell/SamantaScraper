🚀 Google Maps Scraper Web Application

This project is a fully dockerized web platform for extracting business data from Google Maps without using the paid Google Maps API.
It uses:

React + Vite frontend

FastAPI + Selenium + Headless Chromium backend

Django microservice (inscribing_proj) for geospatial inscribing logic

Nginx reverse proxy for serving the frontend and routing API requests

The system supports keyword-based business scraping, coordinate-based queries, task progress tracking, and CSV export — entirely without Google API costs.

✨ Features
🔍 Google Maps Scraper (No Paid API)

Uses Selenium automation + headless Chromium to gather business data from Google Maps.

🖥 Modern Frontend (React + Vite)

Fast, responsive UI with CSV upload, progress indicators, and data export.

⚡ FastAPI Backend

Handles scraping tasks, progress tracking, data processing, and API endpoints.

🌐 Django Inscribing Engine

A separate microservice that calculates inscribed coordinate points used for radius-based map searches.

🐳 Fully Dockerized

All components run through Docker + Docker Compose.

📄 CSV Upload & Result Export

Upload coordinate files and export final scraped results.

🔁 Real-Time Progress

Shows the scraping status so users can monitor long-running tasks.

📁 Project Structure
SamantaScraper/
├── backend/           # FastAPI + Selenium + Chromium scraper
├── frontend/          # React + Vite UI (built and served via Nginx)
├── inscribing_proj/   # Django microservice for geospatial inscribing logic
├── nginx/             # Nginx configuration
├── docker-compose.yml # Full system orchestration
└── README.md

📦 Requirements

Docker

Docker Compose

All dependencies (Python, Node, Chromium, drivers, etc.) are installed inside containers.

▶️ Getting Started
1. Clone the repository
git clone https://github.com/LL01-Business-Dowell/SamantaScraper
cd SamantaScraper

2. Start the full system
docker-compose up --build


This will:

Build the backend (FastAPI + Selenium + Chromium)

Build the inscribing Django microservice

Build the frontend

Start Nginx to serve the frontend and reverse-proxy API calls

Once everything is running:

👉 Open http://localhost
 in your browser.

🧭 How to Use the App

Navigate to http://localhost

Upload a CSV containing:

latitude

longitude

Enter:

a keyword (e.g., restaurants, hotels, salons)

a location (e.g., Mumbai, New York, Berlin)

Click Search

Wait for progress updates (scraping takes time)

When complete, click Download CSV to save results

📂 CSV Format

Your CSV must contain:

latitude,longitude, city, country
19.0760,72.8777,Bengaluru,India
40.7128,-74.0060,Bengaluru,India
...


Any additional columns will be ignored.

🧑‍💻 Development Setup
Frontend
cd frontend
npm install
npm run dev

Backend (FastAPI)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

Inscribing Service (Django)
cd inscribing_proj
pip install -r requirements.txt
python manage.py runserver

⚙️ Technical Overview
Frontend

React + Vite

Axios for API calls

react-csv for CSV export

react-toastify for notifications

Responsive layout with custom CSS

Backend (FastAPI + Selenium)

Headless Chromium scraping

Automatic ChromeDriver handling

Background scraping tasks

Real-time progress tracking

Data cleaning + transformation

Django Inscribing Service

Computes radius-based coordinates

Returns inscribed geographic points

Used by the backend scraper before firing Selenium queries

🐳 Docker Architecture
Containers:
Container	Purpose
frontend	Builds React app (Nginx serves final build)
backend	FastAPI + Selenium + Chromium scraper
inscriber	Django microservice for inscribing logic
nginx	Serves frontend + reverse proxies /api/
Networking

Docker Compose internal hostnames:

backend → http://backend:8000
inscriber → http://inscriber:8002
frontend → built and served via Nginx

Nginx routes
/               → React build
/api/*          → FastAPI backend
