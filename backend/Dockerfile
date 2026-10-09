FROM python:3.12-slim

WORKDIR /deps
COPY vendor/netraom-contracts /deps/netraom-contracts
COPY vendor/netraom-graph-writer /deps/netraom-graph-writer

WORKDIR /app
COPY backend/app ./app
COPY fixtures ./fixtures

RUN pip install --no-cache-dir /deps/netraom-contracts \
    && pip install --no-cache-dir --no-deps /deps/netraom-graph-writer \
    && pip install --no-cache-dir \
        "networkx>=3.2,<4" \
        fastapi \
        uvicorn \
        neo4j \
        sqlalchemy \
        "psycopg[binary]"

ENV PYTHONPATH=/app
ENV FIXTURES_DIR=/app/fixtures/normalized

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
