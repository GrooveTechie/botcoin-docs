FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY seed.py .

# Create directories
RUN mkdir -p data secrets

# Expose port
EXPOSE 8000

# Environment variables
ENV DATABASE_URL=sqlite:///./data/hotel_deals.db
ENV GOOGLE_CLIENT_SECRET_FILE=./secrets/client_secret.json
ENV GOOGLE_TOKEN_FILE=./secrets/token.json
ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
