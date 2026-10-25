FROM python:3.12.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies before code, so code changes reuse the cached pip layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Numeric UID: Kubernetes can only verify runAsNonRoot with a number.
RUN useradd --create-home --uid 10001 appuser
USER 10001

EXPOSE 8000

CMD ["opentelemetry-instrument", "uvicorn", "main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
