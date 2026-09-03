# admindash 静态托管镜像（Vite SPA → nginx）
#
# ⚠️ 根上下文构建（context: .）：admindash 依赖 18 个 workspace 包，pnpm 过滤安装
#    要对齐 lockfile 必须读到完整 workspace manifest，故只能从仓库根构建。
#
# ⚠️ VITE_* 构建期内联，且 admindash **没有**运行时注入兜底：
#    index.html 不加载 runtime-env.js，src/api/client.ts:68 只读
#    import.meta.env.VITE_API_BASE_URL。换 IP / 换域名必须重新 build 本镜像。
ARG NODE_IMAGE=node:20-slim
FROM ${NODE_IMAGE} AS base

ENV PNPM_HOME=/pnpm \
    PATH=/pnpm:$PATH

RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

WORKDIR /app


FROM base AS builder

COPY pnpm-workspace.yaml pnpm-lock.yaml package.json .npmrc ./
COPY packages ./packages
COPY scripts ./scripts

# lockfile 有 5 个 apps/* importer；--frozen-lockfile 要求 workspace importer
# 集合与之一致，故这 5 个 manifest 都得在（只要 package.json，不要源码）。
COPY apps/collab-live/package.json     ./apps/collab-live/
COPY apps/tabtin-web/package.json      ./apps/tabtin-web/
COPY apps/tabtin-daemon/package.json   ./apps/tabtin-daemon/
COPY apps/tabtin-electron/package.json ./apps/tabtin-electron/

COPY apps/admindash ./apps/admindash

# 不能设 NODE_ENV=production —— 否则 pnpm 跳过 devDependencies，vite 缺失。
RUN --mount=type=cache,id=pnpm-store,target=/pnpm/store \
    pnpm install --frozen-lockfile --filter "admindash..."

# admindash 不连 collab-live / Centrifugo，故不需要那两个 WS 变量
ARG VITE_API_BASE_URL
ARG VITE_PUBLIC_WEB_BASE_URL
ARG VITE_AUTH_EMAIL_LOGIN_ENABLED=true

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_PUBLIC_WEB_BASE_URL=${VITE_PUBLIC_WEB_BASE_URL} \
    VITE_AUTH_EMAIL_LOGIN_ENABLED=${VITE_AUTH_EMAIL_LOGIN_ENABLED}

RUN test -n "${VITE_API_BASE_URL}" || (echo "VITE_API_BASE_URL is required" >&2; exit 1)

# 先构建 workspace 依赖闭包，再直接调 vite。
# admindash 的 build 无 prebuild 钩子，但仍跳过 tsc：那是 noEmit 纯类型检查，
# 不产出物，属于 CI 职责，不该卡住部署镜像构建。
RUN pnpm --filter "admindash^..." build \
 && pnpm --filter admindash exec vite build


FROM nginx:alpine AS runtime

COPY apps/admindash/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/apps/admindash/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=5s --retries=6 --start-period=5s \
  CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
