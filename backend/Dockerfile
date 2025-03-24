FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Chrome and dependencies
# RUN apt-get update && apt-get install -y chromium && \
#     wget \
#     gnupg \
#     unzip \
#     xvfb \
#     libxi6 \
#     libgconf-2-4 \
#     libxcomposite1 \
#     libxcursor1 \
#     libxdamage1 \
#     libxext6 \
#     libxfixes3 \
#     libxrandr2 \
#     libxrender1 \
#     libxss1 \
#     libxtst6 \
#     libnss3 \
#     libatk1.0-0 \
#     libatk-bridge2.0-0 \
#     libgtk-3-0 \
#     libgbm1 \
#     && rm -rf /var/lib/apt/lists/*

# First, try to determine which Debian/Ubuntu version we're using
RUN apt-get update && \
    # Install dependencies
    apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    libxi6 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm1 && \
    # Add chromium repo for Debian
    echo "deb http://ftp.debian.org/debian stable main contrib non-free" >> /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y chromium || apt-get install -y chromium-browser || echo "Chromium installation failed, will try alternative" && \
    rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver
RUN CHROMEDRIVER_VERSION=`wget -qO- https://chromedriver.storage.googleapis.com/LATEST_RELEASE` \
    && wget -q --no-verbose -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    && rm /tmp/chromedriver.zip \
    && chmod +x /usr/local/bin/chromedriver

# Set up work directory
WORKDIR /usr/src/app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of application
COPY . /usr/src/app

EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]