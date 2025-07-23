# QA Runner Dockerfile - Multi-platform compatible with Playwright
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Add non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/tests /app/results

# Set environment variables for Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.playwright
ENV PYTHONPATH=/app

# Default command (can be overridden)
CMD ["python", "run_tests.py"]