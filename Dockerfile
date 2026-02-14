# Revvel Music Studio - Docker Image
# Audio processing provided by free and open-source libraries.
#
# Build: docker build -t revvel-music-studio .
# Run API: docker run -p 8000:8000 revvel-music-studio api
# Run CLI: docker run -v $(pwd)/audio:/data revvel-music-studio cli cleanup /data/song.wav

FROM python:3.11-slim

LABEL maintainer="Revvel <revvel@hotrs.music>"
LABEL description="Revvel Music Studio - HOTRS (House of the Rising Sun)"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directories
RUN mkdir -p /app/data/uploads /app/data/output /app/models

# Expose API port
EXPOSE 8000

# Default: run API server
ENTRYPOINT ["python3"]
CMD ["-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
