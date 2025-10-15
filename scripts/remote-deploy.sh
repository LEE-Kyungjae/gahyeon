#!/usr/bin/env bash

set -euo pipefail

echo "========================================="
echo "Deployment Script Started"
echo "========================================="
echo "Script arguments:"
echo "  \$1 (TARGET_ENV): ${1:-<not provided>}"
echo "  \$2 (IMAGE_REPOSITORY): ${2:-<not provided>}"
echo "  \$3 (IMAGE_TAG): ${3:-<not provided>}"
echo ""

TARGET_ENV="${1:-auto}"
IMAGE_REPOSITORY="${2:-}"
IMAGE_TAG="${3:-}"

if [[ -z "${IMAGE_REPOSITORY}" || -z "${IMAGE_TAG}" ]]; then
  echo "ERROR: Missing required arguments" >&2
  echo "Usage: $0 <blue|green|auto> <image-repository> <image-tag>" >&2
  exit 1
fi

echo "Parsed values:"
echo "  TARGET_ENV: ${TARGET_ENV}"
echo "  IMAGE_REPOSITORY: ${IMAGE_REPOSITORY}"
echo "  IMAGE_TAG: ${IMAGE_TAG}"
echo ""

BLUE_PORT="${BLUE_PORT:-8080}"
GREEN_PORT="${GREEN_PORT:-8081}"
HEALTH_PATH="${HEALTH_PATH:-/api/health}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-120}"

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Environment variable ${name} must be provided." >&2
    exit 1
  fi
}

require_env "TOKEN"
require_env "APPLICATION_ID"
require_env "SPOTIFY_CLIENT_ID"
require_env "SPOTIFY_CLIENT_SECRET"
require_env "POSTGRES_PROD_PASSWORD"
require_env "POSTGRES_PROD_HOST"
require_env "POSTGRES_PROD_PORT"
require_env "POSTGRES_PROD_USERNAME"

SPRING_PROFILE="${SPRING_PROFILES_ACTIVE:-prod}"
POSTGRES_HOST="${POSTGRES_PROD_HOST}"
POSTGRES_PORT="${POSTGRES_PROD_PORT}"
POSTGRES_USER="${POSTGRES_PROD_USERNAME}"

resolve_target() {
  local target="$1"
  if [[ "${target}" == "auto" ]]; then
    if docker ps --filter "name=gahyeonbot-green" --filter "status=running" --format '{{.Names}}' | grep -q "gahyeonbot-green"; then
      target="blue"
    else
      target="green"
    fi
  fi

  if [[ "${target}" != "blue" && "${target}" != "green" ]]; then
    echo "Target environment must be 'blue', 'green' or 'auto'." >&2
    exit 1
  fi

  echo "${target}"
}

TARGET="$(resolve_target "${TARGET_ENV}")"
if [[ "${TARGET}" == "blue" ]]; then
  TARGET_PORT="${BLUE_PORT}"
  PREVIOUS_ENV="green"
else
  TARGET_PORT="${GREEN_PORT}"
  PREVIOUS_ENV="blue"
fi

TARGET_CONTAINER="gahyeonbot-${TARGET}"
PREVIOUS_CONTAINER="gahyeonbot-${PREVIOUS_ENV}"

echo "Deploying ${IMAGE_REPOSITORY}:${IMAGE_TAG} to ${TARGET_CONTAINER} (port ${TARGET_PORT})."

echo "Pulling image..."
if ! docker pull "${IMAGE_REPOSITORY}:${IMAGE_TAG}"; then
  echo "ERROR: Failed to pull Docker image" >&2
  exit 1
fi

echo "Stopping and removing old container if exists..."
docker stop "${TARGET_CONTAINER}" >/dev/null 2>&1 || true
docker rm "${TARGET_CONTAINER}" >/dev/null 2>&1 || true

echo "Starting new container with environment variables..."
echo "Server will run on port: ${TARGET_PORT}"
echo "Spring profile: ${SPRING_PROFILE}"
echo "Postgres host: ${POSTGRES_HOST}:${POSTGRES_PORT}"

if ! docker run -d \
  --name "${TARGET_CONTAINER}" \
  --restart unless-stopped \
  --network host \
  -e SERVER_PORT="${TARGET_PORT}" \
  -e TOKEN="${TOKEN}" \
  -e APPLICATION_ID="${APPLICATION_ID}" \
  -e SPOTIFY_CLIENT_ID="${SPOTIFY_CLIENT_ID}" \
  -e SPOTIFY_CLIENT_SECRET="${SPOTIFY_CLIENT_SECRET}" \
  -e APP_CREDENTIALS_TOKEN="${TOKEN}" \
  -e APP_CREDENTIALS_APPLICATION_ID="${APPLICATION_ID}" \
  -e APP_CREDENTIALS_SPOTIFY_CLIENT_ID="${SPOTIFY_CLIENT_ID}" \
  -e APP_CREDENTIALS_SPOTIFY_CLIENT_SECRET="${SPOTIFY_CLIENT_SECRET}" \
  -e POSTGRES_PROD_PASSWORD="${POSTGRES_PROD_PASSWORD}" \
  -e POSTGRES_PROD_HOST="${POSTGRES_HOST}" \
  -e POSTGRES_PROD_PORT="${POSTGRES_PORT}" \
  -e POSTGRES_PROD_USERNAME="${POSTGRES_USER}" \
  -e SPRING_PROFILES_ACTIVE="${SPRING_PROFILE}" \
  "${IMAGE_REPOSITORY}:${IMAGE_TAG}"; then
  echo "ERROR: Failed to start Docker container" >&2
  exit 1
fi

echo "Container started. Checking if it's running..."
sleep 2
if ! docker ps --filter "name=${TARGET_CONTAINER}" --filter "status=running" --format '{{.Names}}' | grep -q "${TARGET_CONTAINER}"; then
  echo "ERROR: Container is not running. Showing logs:" >&2
  docker logs "${TARGET_CONTAINER}" 2>&1 || true
  exit 1
fi

# 두 포트 모두 헬스체크 수행
HEALTH_URL_PRIMARY="http://127.0.0.1:${TARGET_PORT}${HEALTH_PATH}"
HEALTH_URL_8080="http://127.0.0.1:8080${HEALTH_PATH}"
HEALTH_URL_8081="http://127.0.0.1:8081${HEALTH_PATH}"

echo "========================================="
echo "Health Check Configuration"
echo "========================================="
echo "Primary target: ${HEALTH_URL_PRIMARY}"
echo "Monitoring both ports: 8080 and 8081"
echo "Timeout: ${HEALTH_TIMEOUT}s"
echo "========================================="
echo ""

for second in $(seq 1 "${HEALTH_TIMEOUT}"); do
  # 타겟 포트 체크
  HTTP_CODE=$(curl -fsS -o /dev/null -w "%{http_code}" "${HEALTH_URL_PRIMARY}" 2>/dev/null || echo "000")

  # 10초마다 두 포트 모두 상태 출력
  if [[ $((second % 10)) -eq 0 ]]; then
    HTTP_8080=$(curl -fsS -o /dev/null -w "%{http_code}" "${HEALTH_URL_8080}" 2>/dev/null || echo "000")
    HTTP_8081=$(curl -fsS -o /dev/null -w "%{http_code}" "${HEALTH_URL_8081}" 2>/dev/null || echo "000")
    echo "Health check status (${second}s elapsed):"
    echo "  Port 8080: HTTP ${HTTP_8080}"
    echo "  Port 8081: HTTP ${HTTP_8081}"
    echo "  Primary (${TARGET_PORT}): HTTP ${HTTP_CODE}"
  fi

  if [[ "${HTTP_CODE}" == "200" ]]; then
    echo ""
    echo "✓ Health check succeeded after ${second}s (HTTP ${HTTP_CODE})."

    # 최종 상태 확인
    HTTP_8080=$(curl -fsS -o /dev/null -w "%{http_code}" "${HEALTH_URL_8080}" 2>/dev/null || echo "000")
    HTTP_8081=$(curl -fsS -o /dev/null -w "%{http_code}" "${HEALTH_URL_8081}" 2>/dev/null || echo "000")
    echo ""
    echo "Final health check status:"
    echo "  Port 8080: HTTP ${HTTP_8080}"
    echo "  Port 8081: HTTP ${HTTP_8081}"
    echo ""
    break
  fi

  sleep 1
  if [[ "${second}" == "${HEALTH_TIMEOUT}" ]]; then
    echo "" >&2
    echo "✗ Health check failed after ${HEALTH_TIMEOUT}s. Last HTTP code: ${HTTP_CODE}" >&2

    # 실패 시 두 포트 모두 상태 출력
    HTTP_8080=$(curl -fsS -o /dev/null -w "%{http_code}" "${HEALTH_URL_8080}" 2>/dev/null || echo "000")
    HTTP_8081=$(curl -fsS -o /dev/null -w "%{http_code}" "${HEALTH_URL_8081}" 2>/dev/null || echo "000")
    echo "" >&2
    echo "Final health check status:" >&2
    echo "  Port 8080: HTTP ${HTTP_8080}" >&2
    echo "  Port 8081: HTTP ${HTTP_8081}" >&2
    echo "" >&2

    echo "Container logs:" >&2
    docker logs --tail 100 "${TARGET_CONTAINER}" 2>&1 || true
    echo "" >&2
    echo "Cleaning up failed deployment..." >&2
    docker stop "${TARGET_CONTAINER}" || true
    docker rm "${TARGET_CONTAINER}" || true
    exit 1
  fi
done

echo "Stopping previous environment container (${PREVIOUS_CONTAINER}) if running."
docker stop "${PREVIOUS_CONTAINER}" >/dev/null 2>&1 || true
docker rm "${PREVIOUS_CONTAINER}" >/dev/null 2>&1 || true

echo "Pruning unused Docker images older than 7 days and dangling layers."
docker image prune -af --filter "until=168h" >/dev/null 2>&1 || true
docker image prune -f --filter "dangling=true" >/dev/null 2>&1 || true

echo "Deployment to ${TARGET_CONTAINER} completed successfully."
