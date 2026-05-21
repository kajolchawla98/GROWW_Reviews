FROM python:3.11-slim

# Install system deps needed by chromadb/hnswlib
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# Create data directory for SQLite
RUN mkdir -p /app/data

EXPOSE 8080

# Shell form ensures $PORT is expanded from Railway's runtime env
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --log-level info
