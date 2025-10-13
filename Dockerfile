# 1. Base Image 선택 (Java 21 런타임 사용)
FROM eclipse-temurin:21-jre-jammy

# 2. Build Arguments
ARG JAR_FILE=build/libs/gahyeonbot-1.0.0.jar

# 3. 작업 디렉토리 생성 및 설정
WORKDIR /app

# 4. 애플리케이션의 JAR 파일 복사
COPY ${JAR_FILE} /app/bot.jar

# 5. 포트 설정
EXPOSE 8080

# 6. Docker 컨테이너 실행 시 명령어
# 환경 변수를 Spring Boot 프로퍼티로 명시적 전달
ENTRYPOINT ["/bin/sh", "-c", "exec java -Dspring.profiles.active=${SPRING_PROFILES_ACTIVE:-prod} -Dserver.port=${SERVER_PORT:-8080} -Dapp.credentials.token=${TOKEN} -Dapp.credentials.application-id=${APPLICATION_ID} -Dapp.credentials.spotify-client-id=${SPOTIFY_CLIENT_ID} -Dapp.credentials.spotify-client-secret=${SPOTIFY_CLIENT_SECRET} -Djava.security.egd=file:/dev/./urandom -jar /app/bot.jar"]
