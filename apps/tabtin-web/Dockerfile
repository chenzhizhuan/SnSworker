# tabtin-web 静态托管镜像（Vite SPA → nginx）
#
# ⚠️ 根上下文构建（context: .）：tabtin-web 依赖 27 个 workspace 包，pnpm 过滤
#    安装要对齐 lockfile 必须读到完整 workspace manifest，故只能从仓库根构建。
#
# ⚠️ VITE_* 是**构建期**内联：Vite 把 import.meta.env.VITE_* 直接写死进 bundle，
#    运行时改容器环境变量无效。换 IP / 换域名必须重新 build 本镜像。
#    vite.config.ts 用 envDir=repoRoot + loadEnv(mode, repoRoot, '')，容器内没有
#    .env（根 .dockerignore 已排除），因此只有下面这些 ARG→ENV 生效，干净可控。
ARG NODE_IMAGE=node:20-slim
FROM ${NODE_IMAGE} AS base

ENV PNPM_HOME=/pnpm \
    PATH=/pnpm:$PATH

RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

WORKDIR /app


FROM base AS builder

COPY pnpm-workspace.yaml pnpm-lock.yaml package.json .npmrc tsconfig.base.json ./
COPY packages ./packages
COPY scripts ./scripts
COPY contracts ./contracts

# lockfile 有 5 个 apps/* importer；--frozen-lockfile 要求 workspace importer
# 集合与之一致，故这 5 个 manifest 都得在（只要 package.json，不要源码）。
COPY apps/collab-live/package.json     ./apps/collab-live/
COPY apps/admindash/package.json       ./apps/admindash/
COPY apps/tabtin-daemon/package.json   ./apps/tabtin-daemon/
COPY apps/tabtin-electron/package.json ./apps/tabtin-electron/

COPY apps/tabtin-web ./apps/tabtin-web

# 不能设 NODE_ENV=production —— 否则 pnpm 跳过 devDependencies，vite/tsc 缺失。
RUN --mount=type=cache,id=pnpm-store,target=/pnpm/store \
    pnpm install --frozen-lockfile --filter "tabtin-web..."

# 客户端可达地址，全部由 compose 的 build.args 注入
ARG VITE_API_BASE_URL
ARG VITE_PUBLIC_WEB_BASE_URL
ARG VITE_COLLAB_WS_BASE
ARG VITE_CENTRIFUGO_WS_URL
ARG VITE_AUTH_EMAIL_LOGIN_ENABLED=true
ARG VITE_DOC_COLLAB_ENABLED=true
ARG VITE_API_TIMEOUT=30000

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_PUBLIC_WEB_BASE_URL=${VITE_PUBLIC_WEB_BASE_URL} \
    VITE_COLLAB_WS_BASE=${VITE_COLLAB_WS_BASE} \
    VITE_CENTRIFUGO_WS_URL=${VITE_CENTRIFUGO_WS_URL} \
    VITE_AUTH_EMAIL_LOGIN_ENABLED=${VITE_AUTH_EMAIL_LOGIN_ENABLED} \
    VITE_DOC_COLLAB_ENABLED=${VITE_DOC_COLLAB_ENABLED} \
    VITE_API_TIMEOUT=${VITE_API_TIMEOUT}

# 关键地址缺失就早失败，别把打错地址的包发到线上
RUN test -n "${VITE_API_BASE_URL}" || (echo "VITE_API_BASE_URL is required" >&2; exit 1)

# 先构建 workspace 依赖闭包
RUN pnpm --filter "tabtin-web^..." build

# 直接调 vite，绕开 package.json 的 prebuild 钩子。
# 该钩子走 scripts/electron/run-predev-build-with-lock.mjs，带文件锁、为本地多端
# 并行开发设计；Docker 内是串行单进程，上一步已显式构建依赖闭包，不需要它。
# 同时刻意跳过 `tsc`（tabtin-web 的 tsc 是 noEmit 纯类型检查，不产出物）：
# 类型检查属于 CI 职责，不应该让一个类型错误卡住部署镜像构建。
RUN pnpm --filter tabtin-web exec vite build


FROM nginx:alpine AS runtime

COPY apps/tabtin-web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/apps/tabtin-web/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=5s --retries=6 --start-period=5s \
  CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
