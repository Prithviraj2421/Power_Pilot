# PowerPilot backend
#
# Multi-stage so the runtime image carries the installed packages but not pip's
# build machinery or the wheel cache.

FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Dependencies are copied and installed before the source, so editing application
# code does not invalidate the dependency layer on every rebuild.
COPY requirements.txt ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt


FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Runs as an unprivileged user: the container writes uploaded datasets to disk,
# and a compromised process should not own the filesystem.
RUN useradd --create-home --uid 1000 powerpilot

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=powerpilot:powerpilot app ./app

# The dataset registry lives here. Mount a volume over it to keep registered
# datasets across container replacements.
RUN mkdir -p /app/data && chown -R powerpilot:powerpilot /app/data
VOLUME ["/app/data"]

USER powerpilot
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
