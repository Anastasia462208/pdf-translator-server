FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    fonts-dejavu \
    fonts-dejavu-core \
    fonts-dejavu-extra \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p uploads outputs templates

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=web_app.py
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python3", "web_app.py"]

