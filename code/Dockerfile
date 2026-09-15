# Dockerfile for Azure App Service / Azure Container Instances Deployment
FROM python:3.10-slim

WORKDIR /app

# Copy requirements and application code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true

COPY . .

# Add non-root user for security best practices
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Expose port for Azure App Service (default 8000)
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

# Entrypoint for web app execution or terminal batch execution
CMD ["python", "main.py"]

