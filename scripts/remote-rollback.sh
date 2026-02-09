#!/usr/bin/env bash

set -euo pipefail

TARGET_ENV="${1:-auto}"

BLUE_PORT="${BLUE_PORT:-8080}"
GREEN_PORT="${GREEN_PORT:-8081}"
HEALTH_PATH="${HEALTH_PATH:-/api/health}"
DRAIN_PID_FILE="${DRAIN_PID_FILE:-/tmp/gahyeonbot-drain.pid}"
DRAIN_TARGET_FILE="${DRAIN_TARGET_FILE:-/tmp/gahyeonbot-drain.target}"
ACTIVE_UPSTREAM_CONF="${ACTIVE_UPSTREAM_CONF:-/etc/nginx/conf.d/gahyeonbot-upstream.conf}"
NGINX_RELOAD_CMD="${NGINX_RELOAD_CMD:-sudo nginx -s reload}"

write_upstream_conf() {
  local active_env="$1"
  local active_port
  if [[ "${active_env}" == "blue" ]]; then
    active_port="${BLUE_PORT}"
  else
    active_port="${GREEN_PORT}"
  fi

  cat <<EOF
upstream gahyeonbot {
    server 127.0.0.1:${active_port};
}
EOF
}

set_active_upstream() {
  local active_env="$1"
  local tmp_file
  tmp_file="$(mktemp)"
  write_upstream_conf "${active_env}" > "${tmp_file}"
  if ! mv "${tmp_file}" "${ACTIVE_UPSTREAM_CONF}"; then
    echo "ERROR: Failed to update Nginx upstream config at ${ACTIVE_UPSTREAM_CONF}" >&2
    rm -f "${tmp_file}" || true
    exit 1
  fi
  echo "Reloading Nginx (${NGINX_RELOAD_CMD})..."
  if ! eval "${NGINX_RELOAD_CMD}"; then
    echo "ERROR: Nginx reload failed." >&2
    exit 1
  fi
}

cancel_drain() {
  if [[ -f "${DRAIN_PID_FILE}" ]]; then
    local pid
    pid="$(cat "${DRAIN_PID_FILE}" 2>/dev/null || true)"
    if [[ -n "${pid}" ]]; then
      echo "Cancelling scheduled drain (PID: ${pid})..."
      kill "${pid}" >/dev/null 2>&1 || true
    fi
    rm -f "${DRAIN_PID_FILE}" "${DRAIN_TARGET_FILE}" || true
  fi
}

detect_target() {
  local blue_ok="000"
  local green_ok="000"
  blue_ok="$(curl -fsS -o /dev/null -w "%{http_code}" "http://127.0.0.1:${BLUE_PORT}${HEALTH_PATH}" 2>/dev/null || echo "000")"
  green_ok="$(curl -fsS -o /dev/null -w "%{http_code}" "http://127.0.0.1:${GREEN_PORT}${HEALTH_PATH}" 2>/dev/null || echo "000")"

  if [[ "${blue_ok}" == "200" ]]; then
    echo "blue"
    return 0
  fi
  if [[ "${green_ok}" == "200" ]]; then
    echo "green"
    return 0
  fi
  echo "blue"
}

case "${TARGET_ENV}" in
  blue|green)
    TARGET="${TARGET_ENV}"
    ;;
  auto)
    TARGET="$(detect_target)"
    ;;
  *)
    echo "Usage: $0 <blue|green|auto>" >&2
    exit 1
    ;;
esac

if [[ "${TARGET}" == "blue" ]]; then
  PREVIOUS_ENV="green"
else
  PREVIOUS_ENV="blue"
fi

TARGET_CONTAINER="gahyeonbot-${TARGET}"
PREVIOUS_CONTAINER="gahyeonbot-${PREVIOUS_ENV}"

echo "Rollback target: ${TARGET_CONTAINER}"
echo "Failed/previous container candidate: ${PREVIOUS_CONTAINER}"

cancel_drain
set_active_upstream "${TARGET}"

echo "Stopping ${PREVIOUS_CONTAINER} if running..."
docker stop "${PREVIOUS_CONTAINER}" >/dev/null 2>&1 || true
docker rm "${PREVIOUS_CONTAINER}" >/dev/null 2>&1 || true

echo "Rollback complete. Active upstream: ${TARGET}"
