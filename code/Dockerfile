# Dockerfile for Azure App Service / Azure Container Instances Deployment
FROM python:3.10-slim

WORKDIR /app

# Copy requirements and application code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true

COPY . .

# Expose port for Azure App Service (default 8000)
EXPOSE 8000

# Entrypoint for web app execution or terminal batch execution
CMD ["python", "main.py"]
