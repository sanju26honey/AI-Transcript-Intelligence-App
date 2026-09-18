FROM python:3.10-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose port
EXPOSE 7860

# Run with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app", "--timeout", "120"]
