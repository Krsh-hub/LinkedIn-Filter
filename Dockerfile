FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./requirements.txt
COPY web/requirements.txt ./web_requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r web_requirements.txt

# Copy application code
COPY . .

# Expose the default port
EXPOSE 8000

# Run the FastAPI application
CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
