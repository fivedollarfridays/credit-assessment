# Stage 1: Builder — install dependencies
FROM python:3.13-slim AS builder

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Stage 2: Test — verify the build
FROM builder AS test

COPY src/ src/
RUN pip install --no-cache-dir ".[dev]"
RUN python -m pytest src/modules/credit/tests/ --tb=short -q

# Stage 3: Production — minimal runtime image
FROM python:3.13-slim AS production

RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src/ src/

USER appuser

EXPOSE 8000

ENV PYTHONPATH=/app/src \
    ENVIRONMENT=production

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
