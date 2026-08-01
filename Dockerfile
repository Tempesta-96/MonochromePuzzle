FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libasound2 \
        libglib2.0-0 \
        libgl1 \
        libx11-6 \
        libx11-xcb1 \
        libxcb1 \
        libxau6 \
        libxdmcp6 \
        libxext6 \
        libxrender1 \
        libxrandr2 \
        libxcursor1 \
        libxi6 \
        libxfixes3 \
        libxss1 \
        libxkbcommon0 \
        x11-apps \
        x11-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "xor_puzzle.py"]
