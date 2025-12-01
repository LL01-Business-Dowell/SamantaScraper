FROM nginx:1.23.3-alpine

# Copy the nginx configuration
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

# Expose ports for HTTP and HTTPS
EXPOSE 80 443

# Ensure logs are visible in docker logs
RUN mkdir -p /var/log/nginx

# Run nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
