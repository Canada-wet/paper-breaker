FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -e .

EXPOSE 8333
CMD ["paper-breaker-server"]
