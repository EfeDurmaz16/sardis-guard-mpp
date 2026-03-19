FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    "pympp[tempo,server]" \
    "fastapi>=0.115.0" \
    "uvicorn>=0.34.0" \
    "httpx>=0.28.0" \
    "pydantic>=2.0" \
    "scikit-learn>=1.5.0" \
    "numpy>=2.0" \
    "duckdb>=1.0"

# Copy application source
COPY src/ ./src/
COPY pyproject.toml ./

EXPOSE 8402

CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8402"]
