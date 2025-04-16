# Build Stage
FROM node:18-alpine AS build

# Set the working directory for the build stage
WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install


# Copy all the source code
COPY . .

# Build the app for production
RUN npm run build

# Production Stage
FROM nginx:stable-alpine AS production

# Copy the build output from the build stage
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx-spa.conf /etc/nginx/conf.d/default.conf
# Expose the port the app will run on
EXPOSE 80

# Start Nginx to serve the production build
CMD ["nginx", "-g", "daemon off;"]