# RIFT Backend Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies: git (cloning), docker CLI (sandbox orchestration)
# Note: The host's docker socket must be mounted for docker to work
RUN apt-get update && \
    apt-get install -y --no-install-recommends git docker.io && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
