FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY app/ app/
COPY prompts/ prompts/

RUN pip install --no-cache-dir .

RUN addgroup --system app && adduser --system --ingroup app app

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
