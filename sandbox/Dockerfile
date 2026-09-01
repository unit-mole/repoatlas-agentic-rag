FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd \
    --create-home \
    --uid 10001 \
    --shell /usr/sbin/nologin \
    sandbox

COPY requirements-v6-httpx-026.txt \
     /tmp/requirements-v6-httpx-026.txt

RUN python -m pip install \
    --no-cache-dir \
    --upgrade pip \
    && python -m pip install \
    --no-cache-dir \
    -r /tmp/requirements-v6-httpx-026.txt \
    && rm -f /tmp/requirements-v6-httpx-026.txt

WORKDIR /workspace

USER sandbox
