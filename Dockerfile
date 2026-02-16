# 1. Base Image 선택 (Java 21 런타임 사용)
FROM eclipse-temurin:21-jre-jammy

# TTS runtime deps:
# - python3 + pip: run kss splitter + edge-tts CLI
RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 python3-pip ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Python deps for sentence splitting + Edge TTS synthesis.
RUN pip3 install --no-cache-dir kss edge-tts

# 2. Build Arguments
ARG JAR_FILE=build/libs/gahyeonbot-1.0.0.jar

# 3. 작업 디렉토리 생성 및 설정
WORKDIR /app

# 4. 애플리케이션의 JAR 파일 복사
COPY ${JAR_FILE} /app/bot.jar

# TTS helper script.
COPY scripts/tts_split.py /app/tts_split.py

# 5. 포트 설정
EXPOSE 8080

# 6. Docker 컨테이너 실행 시 명령어
# 환경변수: SERVER_PORT (Blue: 8080, Green: 8081), SPRING_PROFILES_ACTIVE (prod)
ENTRYPOINT ["sh","-c","java -Dspring.profiles.active=${SPRING_PROFILES_ACTIVE:-prod} -Dserver.port=${SERVER_PORT:-8080} -Djava.security.egd=file:/dev/./urandom -jar /app/bot.jar"]
