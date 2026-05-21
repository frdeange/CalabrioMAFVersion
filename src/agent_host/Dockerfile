FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY app/ app/
COPY prompts/ prompts/

# Azure CLI for local dev only (DefaultAzureCredential → AzureCliCredential). Not needed in ACA (Managed Identity).
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -sL https://aka.ms/InstallAzureCLIDeb | bash && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir .

RUN addgroup --system app && adduser --system --ingroup app app

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
