# Use a Python base image
FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

# Copy only requirements first for caching
COPY requirements.txt /usr/src/app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . /usr/src/app/

EXPOSE 8002

# Run Django
CMD ["python", "manage.py", "runserver", "0.0.0.0:8002"]
