# Multi-stage build for PDF Translation Service
FROM python:3.11-slim as model-downloader

# Install system dependencies for model download
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy model downloader
COPY scripts/offline_model_downloader.py .
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download model files (this stage ensures model is available)
RUN python offline_model_downloader.py

# Production stage
FROM python:3.11-slim as production

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # For PDF processing
    libmupdf-dev \
    libfreetype6-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    # For fonts and text processing
    fonts-liberation \
    fonts-dejavu-core \
    # Utilities
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY LICENSE README.md ./

# Copy downloaded model from previous stage
COPY --from=model-downloader /app/models ./models

# Copy entrypoint script
COPY docker/entrypoint.sh .
RUN chmod +x entrypoint.sh

# Create directories for file processing
RUN mkdir -p /app/uploads /app/outputs /app/temp && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python src/health_check.py

# Expose port
EXPOSE 8080

# Set environment variables
ENV PYTHONPATH=/app/src
ENV MODEL_PATH=/app/models/Helsinki-NLP/opus-mt-de-en
ENV UPLOAD_PATH=/app/uploads
ENV OUTPUT_PATH=/app/outputs
ENV TEMP_PATH=/app/temp

# Run the application
ENTRYPOINT ["./entrypoint.sh"]
CMD ["python", "src/api_server.py"]