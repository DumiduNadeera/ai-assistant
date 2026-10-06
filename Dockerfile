# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp

WORKDIR /opt/orysys

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

COPY pyproject.toml README.md ./
COPY app ./app
COPY frontend ./frontend
COPY data ./data

RUN python -m pip install --upgrade pip \
    && python -m pip install .

USER 10001:10001

FROM runtime AS api
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

FROM runtime AS frontend
EXPOSE 8501
CMD ["python", "-m", "streamlit", "run", "frontend/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]

