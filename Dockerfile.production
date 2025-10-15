# Production-optimized Dockerfile for DigitalOcean App Platform
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy only production-necessary files (tests excluded by .dockerignore)
COPY . .

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create necessary directories and set permissions
RUN mkdir -p /app/logs && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port (DigitalOcean App Platform uses 8080)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://0.0.0.0:8080/api/health || exit 1

# Production command (single worker, optimized for App Platform)
CMD ["uvicorn", "multi_project_api:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--access-log", "--log-level", "info"]
