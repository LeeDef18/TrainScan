FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port $PORT"]
