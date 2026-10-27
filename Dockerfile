
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY llm_service.py .
COPY rag_service.py .
COPY knowledge_base.json .
COPY log_service.py .
COPY tool_service.py .
COPY tests/ ./tests/

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

