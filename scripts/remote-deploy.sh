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
INTERNAL_PORT="${INTERNAL_PORT:-8080}"
HEALTH_PATH="${HEALTH_PATH:-/api/actuator/health}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-60}"

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

SPRING_PROFILE="${SPRING_PROFILES_ACTIVE:-prod}"

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

if ! docker run -d \
  --name "${TARGET_CONTAINER}" \
  --restart unless-stopped \
  --network host \
  -e SERVER_PORT="${TARGET_PORT}" \
  -e TOKEN="${TOKEN}" \
  -e APPLICATION_ID="${APPLICATION_ID}" \
  -e SPOTIFY_CLIENT_ID="${SPOTIFY_CLIENT_ID}" \
  -e SPOTIFY_CLIENT_SECRET="${SPOTIFY_CLIENT_SECRET}" \
  -e POSTGRES_PROD_PASSWORD="${POSTGRES_PROD_PASSWORD}" \
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

HEALTH_URL="http://127.0.0.1:${TARGET_PORT}${HEALTH_PATH}"
echo "Waiting for health check ${HEALTH_URL} (timeout ${HEALTH_TIMEOUT}s)..."

for second in $(seq 1 "${HEALTH_TIMEOUT}"); do
  HTTP_CODE=$(curl -fsS -o /dev/null -w "%{http_code}" "${HEALTH_URL}" 2>/dev/null || echo "000")
  if [[ "${HTTP_CODE}" == "200" ]]; then
    echo "Health check succeeded after ${second}s (HTTP ${HTTP_CODE})."
    break
  fi

  if [[ $((second % 10)) -eq 0 ]]; then
    echo "Still waiting... (${second}s elapsed, HTTP code: ${HTTP_CODE})"
  fi

  sleep 1
  if [[ "${second}" == "${HEALTH_TIMEOUT}" ]]; then
    echo "Health check failed after ${HEALTH_TIMEOUT}s. Last HTTP code: ${HTTP_CODE}" >&2
    echo "Container logs:" >&2
    docker logs --tail 100 "${TARGET_CONTAINER}" 2>&1 || true
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
