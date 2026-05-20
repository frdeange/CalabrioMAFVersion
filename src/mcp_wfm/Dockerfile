FROM python:3.12-slim
# Sprint 0: tag pin is acceptable; production images should pin by digest.

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system appgroup && adduser --system --uid 1000 --ingroup appgroup appuser

COPY pyproject.toml ./
COPY app ./app

RUN pip install --upgrade pip && pip install .

USER 1000:1000

EXPOSE 8001

CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8001"]
