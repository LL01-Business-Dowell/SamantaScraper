# Use a Python base image
FROM python:3.11

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /usr/src/app

# Install dependencies
COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /usr/src/app/

# Re-add execution permission to manage.py inside the container
RUN chmod +x /usr/src/app/manage.py

# Port the application runs on
EXPOSE 8002

# Command to run the Django development server
# IMPORTANT: It must run on 0.0.0.0 and on the EXPOSEd port
CMD ["python", "manage.py", "runserver", "0.0.0.0:8002"]