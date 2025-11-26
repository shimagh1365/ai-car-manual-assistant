# 1. Use Python 3.11 Slim
FROM python:3.11-slim

# 2. Set working directory to /app
WORKDIR /app

# 3. Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy all files
COPY . .

# 5. Expose port
EXPOSE 8000

# 6. CRITICAL: Add backend to Python path so imports work
ENV PYTHONPATH=/app/backend

# 7. Start the app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]