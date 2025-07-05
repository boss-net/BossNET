FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY dashboards/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy dashboard files
COPY dashboards/ ./dashboards/

# Expose port
EXPOSE 8050

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8050/_dash-layout || exit 1

# Run the dashboard
CMD ["python", "dashboards/student_performance/app.py"]
