FROM python:3.12-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/ ./backend/

# Run the Uvicorn server
# Note: Render provides the PORT environment variable dynamically, but defaults to 10000.
# We explicitly bind Uvicorn to 0.0.0.0 so Render can route traffic to it.
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "10000"]
