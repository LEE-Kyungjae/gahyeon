#!/usr/bin/env bash

set -euo pipefail

TARGET_ENV="${1:-auto}"
IMAGE_REPOSITORY="${2:-}"
IMAGE_TAG="${3:-}"

if [[ -z "${IMAGE_REPOSITORY}" || -z "${IMAGE_TAG}" ]]; then
  echo "Usage: $0 <blue|green|auto> <image-repository> <image-tag>"
  exit 1
fi

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
require_env "POSTGRES_PROD_PASSWORD"

# Spotify credentials are optional
if [[ -z "${SPOTIFY_CLIENT_ID:-}" ]]; then
  echo "Warning: SPOTIFY_CLIENT_ID not set. Spotify features will be disabled."
fi
if [[ -z "${SPOTIFY_CLIENT_SECRET:-}" ]]; then
  echo "Warning: SPOTIFY_CLIENT_SECRET not set. Spotify features will be disabled."
fi

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

docker pull "${IMAGE_REPOSITORY}:${IMAGE_TAG}"

docker stop "${TARGET_CONTAINER}" >/dev/null 2>&1 || true
docker rm "${TARGET_CONTAINER}" >/dev/null 2>&1 || true

# Build docker run command with required env vars
DOCKER_RUN_CMD="docker run -d \
  --name ${TARGET_CONTAINER} \
  --restart unless-stopped \
  -p ${TARGET_PORT}:${INTERNAL_PORT} \
  -e TOKEN=${TOKEN} \
  -e APPLICATION_ID=${APPLICATION_ID} \
  -e POSTGRES_PROD_PASSWORD=${POSTGRES_PROD_PASSWORD} \
  -e SPRING_PROFILES_ACTIVE=${SPRING_PROFILE}"

# Add optional Spotify credentials if present
if [[ -n "${SPOTIFY_CLIENT_ID:-}" ]]; then
  DOCKER_RUN_CMD="${DOCKER_RUN_CMD} -e SPOTIFY_CLIENT_ID=${SPOTIFY_CLIENT_ID}"
fi
if [[ -n "${SPOTIFY_CLIENT_SECRET:-}" ]]; then
  DOCKER_RUN_CMD="${DOCKER_RUN_CMD} -e SPOTIFY_CLIENT_SECRET=${SPOTIFY_CLIENT_SECRET}"
fi

DOCKER_RUN_CMD="${DOCKER_RUN_CMD} ${IMAGE_REPOSITORY}:${IMAGE_TAG}"

eval "${DOCKER_RUN_CMD}"

HEALTH_URL="http://127.0.0.1:${TARGET_PORT}${HEALTH_PATH}"
echo "Waiting for health check ${HEALTH_URL} (timeout ${HEALTH_TIMEOUT}s)..."

for second in $(seq 1 "${HEALTH_TIMEOUT}"); do
  if curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; then
    echo "Health check succeeded after ${second}s."
    break
  fi
  sleep 1
  if [[ "${second}" == "${HEALTH_TIMEOUT}" ]]; then
    echo "Health check failed. Printing logs:"
    docker logs "${TARGET_CONTAINER}" || true
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
