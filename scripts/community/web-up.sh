#!/usr/bin/env bash
# Web 部署形态启动器（Ubuntu 单机 / 公网 IP + HTTP / 13490~13494）。
#
#   SERVER_IP=<公网IP> bash scripts/community/web-up.sh
#
# 与 ./start.sh 的区别：叠加 compose.web.yaml，改端口到 13490~13494，
# 补齐 8 类 Celery worker + beat + collab-live + 两个前端静态站点。
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
env_file="${repo_root}/.env"
web_env_file="${repo_root}/.env.web-runtime"
centrifugo_src="${repo_root}/community-assets/centrifugo.web.template.json.in"
centrifugo_out="${repo_root}/community-assets/centrifugo.web.template.json"
export COMPOSE_DISABLE_ENV_FILE=1

fail() {
  printf 'ERROR: %s\n' "$1" >&2
  exit 1
}

compose() {
  docker compose \
    --project-directory "${repo_root}" \
    --env-file "${env_file}" \
    -f "${repo_root}/compose.yaml" \
    -f "${repo_root}/compose.web.yaml" \
    "$@"
}

# ── 前置检查 ───────────────────────────────────────────────────────────
command -v docker >/dev/null 2>&1 || fail "Docker is not installed."
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is not available."
docker info >/dev/null 2>&1 || fail "Docker Engine is not running."
command -v curl >/dev/null 2>&1 || fail "curl is required for readiness checks."

# ── SERVER_IP：客户端实际可达地址，前端会把它烧进 bundle ────────────────
: "${SERVER_IP:=}"
[[ -n "${SERVER_IP}" ]] || fail \
  "SERVER_IP is required. Example: SERVER_IP=203.0.113.9 bash scripts/community/web-up.sh"
[[ "${SERVER_IP}" =~ ^[A-Za-z0-9.-]+$ ]] || fail \
  "SERVER_IP must be an IPv4 address or hostname. Bare IPv6 is rejected on purpose: it needs bracket form in URLs (http://[::1]:13490), and an unbracketed value would be silently baked into the frontend bundles as a malformed URL."
case "${SERVER_IP}" in
  127.*|localhost|0.0.0.0)
    fail "SERVER_IP must be an address your browser can reach, not loopback. Local OSS rejects loopback public base URLs."
    ;;
esac
export SERVER_IP

# ── 根 .env（沿用既有约定）─────────────────────────────────────────────
bash "${repo_root}/scripts/community/ensure-env-file.sh" "${repo_root}"

# ── COLLAB_LIVE_SECRET：Django ↔ collab-live 的 X-Live-Secret 双向鉴权 ──
# 必须持久化：若每次启动都换值，单独重启某一侧会造成两边不一致。
# collab-live 在 NODE_ENV=production 下要求 ≥16 字符且拒绝 dev 默认值。
if [[ -f "${web_env_file}" ]]; then
  # shellcheck disable=SC1090
  . "${web_env_file}"
fi
if [[ -z "${COLLAB_LIVE_SECRET:-}" ]]; then
  COLLAB_LIVE_SECRET="$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  (umask 077; printf 'COLLAB_LIVE_SECRET=%s\n' "${COLLAB_LIVE_SECRET}" > "${web_env_file}")
  printf 'Generated a new COLLAB_LIVE_SECRET in %s\n' "${web_env_file}"
fi
[[ ${#COLLAB_LIVE_SECRET} -ge 16 ]] || fail \
  "COLLAB_LIVE_SECRET must be at least 16 characters. Delete ${web_env_file} to regenerate."
export COLLAB_LIVE_SECRET

# ── 渲染 Centrifugo web 模板 ───────────────────────────────────────────
# 只替换 __SERVER_ORIGINS__；三个 __CENTRIFUGO_*__ 占位符必须原样留给容器内的
# tabtin.community_secrets 渲染（它校验每个占位符至少出现一次）。
[[ -f "${centrifugo_src}" ]] || fail "Missing Centrifugo template source: ${centrifugo_src}"
origins="\"http://${SERVER_IP}:13490\",\"http://${SERVER_IP}:13491\""
sed "s|__SERVER_ORIGINS__|${origins}|g" "${centrifugo_src}" > "${centrifugo_out}"

if grep -q '__SERVER_ORIGINS__' "${centrifugo_out}"; then
  fail "Centrifugo origins substitution failed; ${centrifugo_out} still has the placeholder."
fi
for marker in __CENTRIFUGO_API_KEY__ __CENTRIFUGO_PROXY_SECRET__ __CENTRIFUGO_TOKEN_SECRET__; do
  if ! grep -q "${marker}" "${centrifugo_out}"; then
    fail "Rendered Centrifugo template lost ${marker}; the in-container renderer requires it."
  fi
done
# JSON 校验是尽力而为：python3 缺失时跳过，容器内渲染器仍会做一次严格解析。
if command -v python3 >/dev/null 2>&1; then
  python3 -c "import json,sys; json.load(open(sys.argv[1]))" "${centrifugo_out}" \
    || fail "Rendered Centrifugo template is not valid JSON: ${centrifugo_out}"
else
  printf 'NOTE: python3 not found; skipping local JSON validation.\n'
fi
printf 'Rendered %s\n' "${centrifugo_out}"

# ── 构建与启动 ─────────────────────────────────────────────────────────
printf '\nBuilding images (first run downloads Playwright/Chromium, expect several minutes)...\n'
compose build

printf '\nStarting the stack...\n'
compose up -d

# ── 就绪探测 ───────────────────────────────────────────────────────────
timeout_seconds="${TABTIN_WEB_START_TIMEOUT_SECONDS:-900}"
poll_seconds="${TABTIN_WEB_START_POLL_SECONDS:-5}"
[[ "${timeout_seconds}" =~ ^[1-9][0-9]*$ ]] || fail "TABTIN_WEB_START_TIMEOUT_SECONDS must be a positive integer."
[[ "${poll_seconds}" =~ ^[1-9][0-9]*$ ]] || fail "TABTIN_WEB_START_POLL_SECONDS must be a positive integer."

wait_for() {
  local label="$1" url="$2" deadline=$((SECONDS + timeout_seconds))
  printf 'Waiting for %s (%s)' "${label}" "${url}"
  until curl -fsS --max-time 3 "${url}" >/dev/null 2>&1; do
    if (( SECONDS >= deadline )); then
      printf '\n'
      compose ps
      fail "${label} did not become ready within ${timeout_seconds}s. Inspect: docker compose -f compose.yaml -f compose.web.yaml logs"
    fi
    printf '.'
    sleep "${poll_seconds}"
  done
  printf ' OK\n'
}

# Django 先起来（它跑迁移与 secrets 初始化），其余服务 depends_on 它 healthy
wait_for 'Django API'   "http://127.0.0.1:13492/health/ready"
wait_for 'collab-live'  "http://127.0.0.1:13493/health"
wait_for 'Centrifugo'   "http://127.0.0.1:13494/health"
wait_for 'tabtin-web'   "http://127.0.0.1:13490/"
wait_for 'admindash'    "http://127.0.0.1:13491/"

printf '\n'
compose ps

cat <<EOF

========================================
TabTin Web stack is READY
========================================

  Web workspace   http://${SERVER_IP}:13490
  Admin console   http://${SERVER_IP}:13491
  Django API      http://${SERVER_IP}:13492
  Collab WS       ws://${SERVER_IP}:13493
  Centrifugo WS   ws://${SERVER_IP}:13494

  PostgreSQL / Redis are intentionally NOT published to the host.

Open ports 13490-13494 in your firewall / cloud security group, e.g.:
  sudo ufw allow 13490:13494/tcp

Known limitations of the public-IP + HTTP profile:
  1. Organization invitation links are unavailable. invitation_service.py
     requires HTTPS or a private-LAN HTTP host and raises otherwise.
  2. DEBUG=True — error pages expose stack traces. This is a dogfood
     profile, not a hardened public production posture.
  3. Frontend addresses are baked into the images at build time. Changing
     SERVER_IP requires rebuilding tabtin-web and admindash.

Verify queue coverage (expect all 14 registered queues):
  docker compose -f compose.yaml -f compose.web.yaml exec worker-default \\
    celery -A tabtin inspect active_queues

Follow logs:
  docker compose -f compose.yaml -f compose.web.yaml logs -f
EOF
