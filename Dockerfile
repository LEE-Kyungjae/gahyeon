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

# 6. 환경 변수 설정
ENV JAVA_OPTS=""

# 7. Docker 컨테이너 실행 시 명령어
# JAVA_OPTS 환경 변수를 통해 JVM 옵션 전달 가능
ENTRYPOINT sh -c "java $JAVA_OPTS -Djava.security.egd=file:/dev/./urandom -jar /app/bot.jar"
