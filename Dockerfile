# syntax=docker/dockerfile:1
# Imagen de la API (monolito modular). La misma imagen se usa en local (docker compose) y,
# en el Sprint 4, como base de cada servicio extraído a EKS.
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

FROM base AS deps
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

FROM base AS runtime
RUN useradd --uid 10001 --create-home appuser
COPY --from=deps /install /usr/local
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser main.py .
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health').status==200 else 1)"
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
