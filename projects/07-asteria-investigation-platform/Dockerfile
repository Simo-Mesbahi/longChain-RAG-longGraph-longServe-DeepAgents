FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

RUN addgroup --system asteria && adduser --system --ingroup asteria asteria

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY projects/02-documentary-rag-assistant/data ./projects/02-documentary-rag-assistant/data
COPY projects/07-asteria-investigation-platform ./projects/07-asteria-investigation-platform

RUN python -m pip install --upgrade pip && python -m pip install ".[api]"

USER asteria

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["uvicorn", "api:app", "--app-dir", "projects/07-asteria-investigation-platform", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
