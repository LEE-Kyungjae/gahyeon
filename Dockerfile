# 1. Base Image 선택 (Java 21 런타임 사용)
FROM eclipse-temurin:21-jre-jammy

# Piper/KSS runtime deps:
# - python3 + pip: run kss splitter + piper-tts CLI
# - libsndfile1: piper-tts runtime dependency on many distros
RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 python3-pip libsndfile1 ca-certificates curl \
  && rm -rf /var/lib/apt/lists/*

# Python deps for offline sentence splitting + TTS synthesis.
# piper-tts CLI import needs pathvalidate in some versions/environments; install explicitly for safety.
RUN pip3 install --no-cache-dir kss piper-tts pathvalidate

# 2. Build Arguments
ARG JAR_FILE=build/libs/gahyeonbot-1.0.0.jar

# 3. 작업 디렉토리 생성 및 설정
WORKDIR /app

# 4. 애플리케이션의 JAR 파일 복사
COPY ${JAR_FILE} /app/bot.jar

# TTS helper script.
COPY scripts/tts_split.py /app/tts_split.py

# Bundle community Korean female model (neurlang/piper-onnx-kss-korean).
# You can override all values at build time if you want to swap model later.
ARG TTS_MODEL_REPO=https://huggingface.co/neurlang/piper-onnx-kss-korean/resolve/main
ARG TTS_MODEL_FILE=piper-kss-korean.onnx
ARG TTS_MODEL_CONFIG_FILE=piper-kss-korean.onnx.json
ENV TTS_MODEL_DIR=/app/tts_models
RUN mkdir -p "$TTS_MODEL_DIR" \
  && curl -fL "$TTS_MODEL_REPO/$TTS_MODEL_FILE" -o "$TTS_MODEL_DIR/$TTS_MODEL_FILE" \
  && curl -fL "$TTS_MODEL_REPO/$TTS_MODEL_CONFIG_FILE" -o "$TTS_MODEL_DIR/$TTS_MODEL_CONFIG_FILE"

# 5. 포트 설정
EXPOSE 8080

# 6. Docker 컨테이너 실행 시 명령어
# 환경변수: SERVER_PORT (Blue: 8080, Green: 8081), SPRING_PROFILES_ACTIVE (prod)
ENTRYPOINT ["sh","-c","java -Dspring.profiles.active=${SPRING_PROFILES_ACTIVE:-prod} -Dserver.port=${SERVER_PORT:-8080} -Djava.security.egd=file:/dev/./urandom -jar /app/bot.jar"]
