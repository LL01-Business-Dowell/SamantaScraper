# Use official Node.js LTS version
FROM node:18

# Set work directory inside container
WORKDIR /usr/src/app

# Copy package.json and package-lock.json first (Handle missing lock file)
COPY package*.json ./

# Install dependencies (fallback to npm install if package-lock.json is missing)
RUN npm install

RUN npm install -g vite

# Copy all project files
COPY . .

# Ensure proper file permissions
RUN chmod -R 777 /usr/src/app

# Expose port for frontend app (Vite default is 5173)
EXPOSE 5173

# Start the app
CMD ["npm", "run", "dev"]
