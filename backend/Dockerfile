# Hugging Face Space (Docker SDK) — unified Python backend (ML + Groq AI)
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app + model
COPY . .

# Hugging Face Spaces route traffic to port 7860
ENV PORT=7860
EXPOSE 7860

# 2 workers, long timeout so the first (cold) Groq call doesn't get killed
CMD ["gunicorn", "-b", "0.0.0.0:7860", "-w", "2", "--timeout", "120", "app:app"]
