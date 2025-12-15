FROM python:3.11-slim AS builder

WORKDIR /build

# whisper.cpp build deps + ffmpeg for runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    build-essential \
    cmake \
    pkg-config \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Build whisper.cpp (produces whisper-cli)
RUN git clone --depth 1 https://github.com/ggerganov/whisper.cpp.git /build/whisper.cpp \
    && cmake -S /build/whisper.cpp -B /build/whisper.cpp/build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build /build/whisper.cpp/build -j


FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy whisper-cli binary
COPY --from=builder /build/whisper.cpp/build/bin/whisper-cli /usr/local/bin/whisper-cli

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/ /app/backend/
COPY index.html /app/index.html
COPY config.example.json /app/config.example.json

ENV HOST=0.0.0.0
ENV PORT=8000
ENV DEBUG=0
ENV WHISPER_BIN=whisper-cli
ENV WHISPER_LANGUAGE=zh
ENV WHISPER_MODEL=/models/ggml-small.bin
ENV MAX_CONTENT_LENGTH_MB=1024

EXPOSE 8000

CMD ["python", "backend/app.py"]


