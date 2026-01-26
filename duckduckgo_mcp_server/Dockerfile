FROM python:3.11-slim

WORKDIR /app

# Install dependencies with proxy support
COPY requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt || \
    pip install --no-cache-dir -r requirements.txt --index-url https://pypi.org/simple

# Copy application code
COPY server.py .

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/mcp')" || exit 1

# Run application
CMD ["python", "server.py"]
