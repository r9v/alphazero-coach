# Stage 1: Build frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + game engine
FROM python:3.10-slim AS backend

# Install build tools for Cython compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clone and build the game engine
RUN git clone --depth 1 https://github.com/r9v/alphazero-boardgames.git /app/alphazero-engine
WORKDIR /app/alphazero-engine
RUN pip install --no-cache-dir numpy cython \
    && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && python setup.py build_ext --inplace

# Install coach dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY core/ ./core/
COPY data/ ./data/
COPY .env.example ./.env.example

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Set engine path
ENV ALPHAZERO_DIR=/app/alphazero-engine
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "core.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
