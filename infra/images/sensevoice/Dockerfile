FROM python:3.12-slim

ARG MODEL_URL=https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2
ARG MODEL_SHA256=7d1efa2138a65b0b488df37f8b89e3d91a60676e416f515b952358d83dfd347e

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl bzip2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

RUN mkdir -p /models/sensevoice \
    && curl -fL "${MODEL_URL}" -o /tmp/sensevoice.tar.bz2 \
    && echo "${MODEL_SHA256}  /tmp/sensevoice.tar.bz2" | sha256sum -c - \
    && tar -xjf /tmp/sensevoice.tar.bz2 -C /tmp \
    && model_dir="$(find /tmp -maxdepth 1 -type d -name 'sherpa-onnx-sense-voice-*' | head -1)" \
    && cp "${model_dir}/model.int8.onnx" "${model_dir}/tokens.txt" /models/sensevoice/ \
    && rm -rf /tmp/sensevoice.tar.bz2 "${model_dir}"

COPY server.py /app/server.py
WORKDIR /app

ENV SENSEVOICE_MODEL_DIR=/models/sensevoice \
    SENSEVOICE_NUM_THREADS=8

EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
