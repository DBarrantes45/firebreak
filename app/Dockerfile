# Base image: official Python, "slim" variant (Debian without extra tools).
# Pinned to an exact version so the build gives the same result tomorrow.
# Same Python version as the local .venv (3.12), so local and container match.
FROM python:3.12.15-slim

# PYTHONDONTWRITEBYTECODE: do not write .pyc files inside the image.
# PYTHONUNBUFFERED: print logs right away, so "docker compose logs"
# shows them in real time instead of in delayed chunks.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Every following command runs inside /app.
WORKDIR /app

# Step 1: dependencies first.
# Docker caches every step. While requirements.txt does not change,
# this slow step is reused and the rebuild takes seconds.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 2: the code, after the dependencies.
# The code changes often; copying it last means a code change
# does not force pip to install everything again.
# Only src/ is copied: tests/ and requirements.in stay out of the image.
COPY src/ ./src/

# Step 3: an unprivileged user.
# If someone breaks into the app, they are not root inside the container.
# USER uses the numeric id, not the name: Kubernetes (runAsNonRoot) can only
# verify that a container is not root when the user is a number.
RUN useradd --create-home --uid 10001 appuser
USER 10001

# Documents the port the app listens on (it does not publish it;
# compose.yaml does that).
EXPOSE 8000

# Start the API.
# --host 0.0.0.0: listen on every interface of the container. With the
# default 127.0.0.1 it would only accept connections from inside itself,
# and nothing outside the container could reach it.
# No --reload here: that is only for development on your machine.
CMD ["uvicorn", "main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]