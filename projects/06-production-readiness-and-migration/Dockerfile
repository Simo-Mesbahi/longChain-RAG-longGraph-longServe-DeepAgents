FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY projects ./projects

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -e ".[rag,api]"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python projects/06-production-readiness-and-migration/app.py health | grep '"status": "ok"' || exit 1

CMD ["uvicorn", "api:app", "--app-dir", "projects/06-production-readiness-and-migration", "--host", "0.0.0.0", "--port", "8000"]
