# Use official Python 3.12 image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml first for better caching
COPY pyproject.toml README.md ./

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install .

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads/temp

# Run gunicorn
CMD gunicorn app:app --bind 0.0.0.0:${PORT:-8080} --workers 4 --timeout 120 --access-logfile - --error-logfile -
