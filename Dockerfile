
# STAGE 1 - Build React frontend
FROM node:24-alpine AS frontend-build

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# STAGE 2 - FastAPI backend
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Existing backend files
COPY app.py .
COPY llm_service.py .
COPY rag_service.py .
COPY knowledge_base.json .
COPY log_service.py .
COPY tool_service.py .
COPY tests/ ./tests/
COPY database.py .

# Copy compiled React frontend
COPY --from=frontend-build /frontend/dist ./frontend/dist

# SQLite and simulated log storage
RUN mkdir -p /app/data

EXPOSE 8000

# Use Render's PORT environment variable
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
