# Collab Live 运行镜像（Hocuspocus Y.js 统一实时协作服务）
#
# ⚠️ 根上下文构建（context: .）：collab-live 依赖 workspace 包 @tabtin/config
#    (= packages/tabtin-config，注意不是 packages/app-config，那个叫
#    @tabtin/app-config)、@tabtin/doc-editor、@tabtin/table-engine，后者又传递
#    依赖 @tabtin/collab-core 与 @tabtin/table-core。pnpm 过滤安装要对齐 lockfile
#    必须读到完整 workspace manifest，故只能从仓库根构建。
#
# 依赖闭包（10 个 workspace 包）经核对不含原生模块与 postinstall 脚本，过滤安装
# 可避开 Electron/桌面端那批重依赖。根 package.json 的 prepare(setup-git-hooks.mjs)
# 在非 git worktree 下自行 exit 0，因此无需 --ignore-scripts。
#
# 运行产物走 tsc 编译后的 dist/：源码相对 import 全部带 .js 后缀，Node ESM 可直接
# 执行，生产不引入 tsx。
ARG NODE_IMAGE=node:20-slim
FROM ${NODE_IMAGE} AS base

ENV PNPM_HOME=/pnpm \
    PATH=/pnpm:$PATH

RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

WORKDIR /app


FROM base AS builder

# workspace 骨架 + 全量 packages（根 .dockerignore 已剔除 node_modules/dist）
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json .npmrc ./
COPY scripts ./scripts
COPY packages ./packages

# pnpm-workspace.yaml 的 apps/* glob 对应 lockfile 里 5 个 importer。
# --frozen-lockfile 要求 workspace importer 集合与 lockfile 一致，因此这 5 个
# manifest 都得在（只要 package.json，不要源码）。缺了 pnpm 会判 lockfile 过期。
COPY apps/tabtin-web/package.json      ./apps/tabtin-web/
COPY apps/admindash/package.json       ./apps/admindash/
COPY apps/tabtin-daemon/package.json   ./apps/tabtin-daemon/
COPY apps/tabtin-electron/package.json ./apps/tabtin-electron/

COPY apps/collab-live ./apps/collab-live

# 过滤安装：只装 collab-live 及其 workspace 闭包。
# 此处**不能**设 NODE_ENV=production —— 否则 pnpm 跳过 devDependencies，
# typescript 缺失会让下一步 build 直接失败。
RUN --mount=type=cache,id=pnpm-store,target=/pnpm/store \
    pnpm install --frozen-lockfile --filter "collab-live..."

# 先构建 workspace 依赖（tsc 需要各包的 dist/*.d.ts），再构建自身
RUN pnpm --filter "collab-live^..." build \
 && pnpm --filter collab-live build


FROM base AS runtime

# 取舍说明：整树 COPY 而非 pnpm deploy --prod。
# pnpm 的 node_modules 是指向 .pnpm 的符号链接树，workspace 依赖还额外链到
# /app/packages/*。跨 stage 只挑部分目录极易断链，且本机无 Docker 无法验证。
# 这里选择「与构建时完全一致的树」换取确定性，代价是镜像含 devDependencies。
# 后续若要瘦身，在服务器上验证过 pnpm deploy 再切换。
ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=4100

# 建用户必须在 COPY 之前：这样 COPY --chown 一次落盘即带属主。
# 若先 COPY 再 chown -R，会把整棵树重写进一个新层，镜像体积近乎翻倍。
RUN groupadd --gid 10001 collab-live \
    && useradd --uid 10001 --gid 10001 --home-dir /app --shell /usr/sbin/nologin collab-live

COPY --from=builder --chown=10001:10001 /app /app

USER collab-live

EXPOSE 4100

# node:20-slim 无 curl/wget；用 Node 20 内置 fetch 探活。
# /health 免鉴权且跳过限流（src/server.ts）。
HEALTHCHECK --interval=10s --timeout=5s --retries=12 --start-period=15s \
  CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||4100)+'/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "apps/collab-live/dist/start.js"]
