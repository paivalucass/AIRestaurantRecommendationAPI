# Use slim to reduce image size
FROM python:3.10-slim

# Avoid Python writing pycache
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install OS dependencies (needed for FAISS & sentence-transformers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install dependencies first so Docker caches this layer
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project
COPY . /app/

# Expose API port
EXPOSE 8000

# Start FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
