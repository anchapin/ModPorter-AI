# Stage 1: Build the Python application
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Ensure the application runs as a non-root user for security
RUN useradd --create-home appuser
WORKDIR /home/appuser/app
COPY --chown=appuser:appuser . /home/appuser/app
USER appuser

# Expose the port the app runs on
EXPOSE 8001

# Command to run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
