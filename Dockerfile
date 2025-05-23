# Use official Python slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code and wait script
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Default command just runs uvicorn; migrations will run in docker-compose command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
