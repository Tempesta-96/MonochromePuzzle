FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYGAME_HIDE_SUPPORT_PROMPT=1
ENV SDL_VIDEODRIVER=dummy
ENV SDL_AUDIODRIVER=dummy

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libasound2 \
        libgl1 \
        libglib2.0-0 \
        libx11-6 \
        libxext6 \
        libxrender1 \
        libxrandr2 \
        libxcursor1 \
        libxi6 \
        libxfixes3 \
        libxss1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "xor_puzzle.py", "--web", "--host", "0.0.0.0", "--port", "8000"]
