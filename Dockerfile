# -------------------------------------------------------
# Mint Maths Flask App - Fly.io Deployment
# -------------------------------------------------------
FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create app directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN apt-get update && apt-get install -y \
    libglib2.0-0 libsm6 libxrender1 libxext6 ghostscript \
    && pip install --upgrade pip \
    && pip install -r requirements.txt \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy all source code
COPY . /app

# Expose the port Fly.io expects
EXPOSE 8080

# Environment variables for Flask
ENV PORT=8080
ENV FLASK_ENV=production

# Gunicorn handles concurrency and keeps memory stable
CMD ["gunicorn", "-w", "2", "-k", "gthread", "--threads", "4", "-b", "0.0.0.0:8080", "app:app"]
