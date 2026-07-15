FROM python:3.12-slim

# Prevent Python from writing .pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1
# Prevent Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/ ./backend/

# Expose port for Back4App
EXPOSE 8080

# Run the Uvicorn server
# We must cd into the backend directory so 'from app.config import settings' resolves correctly!
CMD sh -c "cd backend && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"
