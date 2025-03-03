# Use full Debian-based image (not slim)
FROM python:3.11

# Set the working directory
WORKDIR /usr/src/app

# Install dependencies for Selenium & Chrome
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends -f \
    wget curl unzip gnupg \
    libx11-6 libxcb1 libxcomposite1 libxdamage1 libxext6 libxfixes3 \
    libxkbcommon0 libxrandr2 xdg-utils libglib2.0-0 libnss3 libgconf-2-4 \
    libx11-xcb1 libxcursor1 libxi6 libxrender1 libdbus-glib-1-2 libgtk-3-0 && \
    rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN apt-get update --fix-missing && apt-get install -f -y && \
    wget -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y /tmp/chrome.deb && rm /tmp/chrome.deb

# Set Chrome binary path for Selenium
ENV GOOGLE_CHROME_BIN=/usr/bin/google-chrome

# Install Chromedriver directly (fixed)
RUN wget -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/133.0.6943.53/linux64/chromedriver-linux64.zip && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    rm /tmp/chromedriver.zip && \
    ln -s /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver

# Set Chromedriver path for Selenium
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

# Copy requirements file
COPY requirements.txt /usr/src/app/requirements.txt

# Install Python dependencies with specific versions
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir numpy==1.26.0 && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /usr/src/app

# Create volume for output data
VOLUME ["/usr/src/app/output"]

# Run the script
CMD ["python", "app.py"]