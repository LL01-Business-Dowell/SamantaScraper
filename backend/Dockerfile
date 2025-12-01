# Use full Python image for better compatibility
FROM python:3.11

# Set working directory
WORKDIR /usr/src/app

# Install system dependencies required for Chromium & Selenium
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        wget curl unzip gnupg xdg-utils fonts-liberation \
        libx11-6 libxcb1 libxcomposite1 libxdamage1 libxext6 \
        libxfixes3 libxkbcommon0 libxrandr2 libglib2.0-0 libnss3 \
        libx11-xcb1 libxcursor1 libxi6 libxrender1 libdbus-glib-1-2 libgtk-3-0 \
        libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3 libexpat1 libgbm1 \
        libnspr4 libpango-1.0-0 libvulkan1 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Set Chromium binary path
ENV GOOGLE_CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV PATH="/usr/bin:${PATH}"

# Copy application code
COPY . .

# Expose backend port
EXPOSE 8000

# Create startup script to install dependencies at container start
RUN echo '#!/bin/bash\n\
pip install --no-cache-dir --upgrade pip && \\\n\
pip install --no-cache-dir -r requirements.txt selenium uvicorn && \\\n\
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 300' > /usr/src/app/start.sh \
    && chmod +x /usr/src/app/start.sh

# Run the startup script
CMD ["/usr/src/app/start.sh"]
