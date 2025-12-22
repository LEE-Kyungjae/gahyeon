# 가현봇 (GahyeonBot)
```
연인과 취침전에 보이스채널을 나가는 번거로움을 겪어보신적 있으신가요?
다른 보이스채널 유저에게 공지사항이있어 모두 보이스채널로 집결시키고싶진 않으신가요?
가현봇이 해결해줍니다!
```

가현봇은 디스코드 서버에서 예약 관리 및 일정 조율을 돕는 봇입니다. 간단한 명령어 입력으로 예약 생성, 취소, 조회 기능을 제공합니다.

## 주요 기능
- **나가기 예약 생성:** 특정 날짜와 시간에 나가기 예약 생성
- **같이나가기 예약 생성:** 여러 사람이 함께 나가는 예약 생성
- **예약 취소:** 기존 예약 취소
- **예약 목록 조회:** 모든 예약된 목록 확인
- **뮤직봇 기능:** 음악 재생, 일시 정지, 스킵 등 기본 음악 관리 기능 제공

---

## 사용 방법
### 1. 봇 초대
가현봇을 디스코드 서버에 초대하세요.
[가현봇 초대 링크](https://discord.com/oauth2/authorize?client_id=1220338955082399845)
[가현봇 위키](https://github.com/LEE-Kyungjae/gahyeonbot/wiki)
### 2. 명령어 사용
디스코드 채팅 창에 다음과 같은 명령어를 입력하세요:

- **나가기 예약 생성:**
  ```
  Out [날짜] [시간] [설명(선택)]
  ```
  예: `Out 2024-12-25 18:00 크리스마스 파티`

- **같이나가기 예약 생성:**
  ```
  WithOut [날짜] [시간] [설명(선택)]
  ```
  예: `WithOut 2024-12-31 23:30 연말 카운트다운`

- **예약 취소:**
  ```
  CancelOut [예약 번호]
  ```
  예: `CancelOut 1`

- **예약 목록 조회:**
  ```
  SearchOut
  ```
  예: `SearchOut`
## 설치 및 실행
가현봇은 Java 21과 Spring Boot 3 기반으로 제작되었으며, JDA와 LavaPlayer를 사용합니다.

### 요구 환경
- Java 21 (OpenJDK/Eclipse Temurin 권장)
- Gradle Wrapper (프로젝트에 포함)
- Discord Bot Token 및 Spotify API 자격 증명
- 로컬 개발용 PostgreSQL (docker-compose로 제공)

### 필수 환경 변수
다음 값은 애플리케이션 실행 전에 환경 변수로 설정해야 합니다.

| 변수 | 설명 |
| --- | --- |
| `TOKEN` | Discord 봇 토큰 |
| `APPLICATION_ID` | Discord 애플리케이션 ID |
| `SPOTIFY_CLIENT_ID` | Spotify Client ID |
| `SPOTIFY_CLIENT_SECRET` | Spotify Client Secret |
| `OPENAI_API_KEY` | OpenAI API 키 (가현아 AI 대화 기능) |
| `POSTGRES_DEV_PASSWORD` | 개발용 Postgres 비밀번호 (`application-dev.yml` 참고) |

### 1. 프로젝트 클론
```bash
git clone https://github.com/LEE-Kyungjae/gahyeonbot.git
cd gahyeonbot
```

### 2. 개발용 데이터베이스 (선택)
로컬에서 PostgreSQL을 실행하려면 다음 명령으로 컨테이너를 띄울 수 있습니다.
```bash
docker compose up -d postgres-dev
```
(기본 설정은 `localhost:5433` 포트로 매핑됩니다.)

### 3. 빌드 및 실행
```bash
./gradlew clean shadowJar
java -jar build/libs/gahyeonbot-1.0.0.jar --spring.profiles.active=dev
```
> 기본 실행(`--spring.profiles.active` 생략)은 `dev` 프로필이며 PostgreSQL·Flyway·Discord 연동이 모두 켜진 상태입니다. 로컬 개발 시 `docker compose up -d postgres-dev`로 DB를 띄우고 필요한 환경 변수를 설정하세요. 만약 Discord 봇 연결을 잠시 끄고 싶다면 `BOT_ENABLED=false ./gradlew bootRun`처럼 환경 변수로 제어할 수 있습니다.

### 4. Docker 이미지로 실행 (선택)
```bash
docker build -t gahyeonbot:latest .
docker run --rm -p 8080:8080 \
  -e TOKEN=your_token \
  -e APPLICATION_ID=your_app_id \
  -e SPOTIFY_CLIENT_ID=your_client_id \
  -e SPOTIFY_CLIENT_SECRET=your_client_secret \
  -e POSTGRES_DEV_PASSWORD=your_password \
  gahyeonbot:latest
```
Dockerfile은 Java 21 JRE(Eclipse Temurin)를 기반으로 하며, `docker-compose.yml`은 개발용 Postgres 컨테이너만 제공합니다.

## CI/CD & 배포 전략
- **CI**: GitHub Actions 워크플로(`.github/workflows/ci-cd.yml`)가 PR·main 브랜치 푸시에서 `./gradlew clean test`를 실행합니다.
- **버전 태깅**: main 브랜치에 머지되면 자동으로 패치 버전 태그(`vX.Y.Z`)가 생성되고 GHCR에 새 Docker 이미지가 빌드·푸시됩니다.
- **CD**: 같은 워크플로에서 프로덕션 환경 승인 후 SSH를 통해 `scripts/remote-deploy.sh`를 실행하여 Blue/Green 컨테이너를 교대 배포합니다.
- **헬스체크**: 컨테이너 기동 후 `/api/health` 응답을 확인한 뒤 이전 환경 컨테이너를 정리합니다. 실패 시 새 컨테이너를 중단하고 로그를 출력합니다.

### GitHub Actions Secrets
배포를 위해 아래 시크릿을 저장해야 합니다.

| 이름 | 설명 |
| --- | --- |
| `TOKEN` | Discord 봇 토큰 |
| `APPLICATION_ID` | Discord 애플리케이션 ID |
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | Spotify API 자격 증명 |
| `OPENAI_API_KEY` | OpenAI API 키 (가현아 AI 대화 기능) |
| `POSTGRES_PROD_PASSWORD` | 운영용 Postgres 비밀번호 (`application-prod.yml`) |
| `SSH_HOST` / `SSH_PORT` / `SSH_USER` / `SSH_KEY` | 배포 대상 서버 접근 정보 (OpenSSH private key) |

필요시 아래 변수를 추가로 설정할 수 있습니다.

| 이름 | 설명 |
| --- | --- |
| `BLUE_PORT` / `GREEN_PORT` | Blue/Green 컨테이너가 노출할 호스트 포트 (기본 8080/8081) |
| `HEALTH_PATH` | 헬스체크 엔드포인트 (기본 `/api/health`) |
| `POSTGRES_PROD_HOST` | 운영 Postgres 호스트명 (기본 `postgres.internal`) |
| `POSTGRES_PROD_PORT` | 운영 Postgres 포트 (기본 `5432`) |
| `POSTGRES_PROD_USERNAME` | 운영 Postgres 사용자명 (기본 `gahyeonbot_app`) |

> **참고:** `scripts/remote-deploy.sh`는 원격 서버에 전달되어 실행되므로, 서버 측에서 Docker가 설치되어 있고 GHCR 이미지를 가져올 수 있어야 합니다. 최초 실행 전에는 `chmod +x scripts/remote-deploy.sh`로 실행 권한을 부여하세요.

## 기여하기
1. 이슈 등록
2. Fork 후 새 브랜치 생성
3. 수정 후 Pull Request 제출

---

## 라이선스
이 프로젝트는 [MIT 라이선스](LICENSE)를 따릅니다.<br>
해당 조건하에 누구나 가현봇을 확장하여 자신이 원하는 봇을 만드시는게 가능합니다.

---

## 문의
- 개발자: [LEE-Kyungjae](https://github.com/LEE-Kyungjae)
- 이메일: ze2@kakao.com
