---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '2a3b9adc-bc10-437f-8074-ab4ce0fb5039'
  PropagateID: '2a3b9adc-bc10-437f-8074-ab4ce0fb5039'
  ReservedCode1: '5c4503ef-b6fc-4a3c-9554-7393fcdd55a4'
  ReservedCode2: '5c4503ef-b6fc-4a3c-9554-7393fcdd55a4'
---

# Web 侧 Docker 部署（Ubuntu 单机 / 公网 IP + HTTP / 13490~13494）

面向自建服务器的 web 部署形态：`compose.yaml` 之上叠加 `compose.web.yaml`，
把端口改到 13490~13494，并补齐 collab-live、两个前端静态站点、8 类 Celery
worker 与 celery beat。

Electron 桌面端、iOS、Android、CLI、SDK 不在本形态范围内。

## 快速开始

```bash
# 放行端口（云服务器还需在安全组同步放行）
sudo ufw allow 13490:13494/tcp

SERVER_IP=<你的公网IP> bash scripts/community/web-up.sh
```

首次构建要装 Playwright/Chromium 与全部前端依赖，耗时通常十几分钟。

## 端口

| 宿主机 | 服务 | 容器内 | 说明 |
|---|---|---|---|
| 13490 | tabtin-web | 80 | Web 工作台 / 公开分享页 |
| 13491 | admindash | 80 | 运营管理台 |
| 13492 | django | 6060 | REST API + WebSocket |
| 13493 | collab-live | 4100 | Y.js 协作 WS |
| 13494 | centrifugo | 8100 | 实时消息 WS |
| — | postgres | 5432 | **刻意不映射**，仅容器网络 |
| — | redis | 6379 | **刻意不映射**，仅容器网络 |
| — | worker × 8 + beat | — | 无监听端口 |

Redis DB 分配：Django `0/1/2`、Centrifugo `13`、collab-live `14`。

## 服务清单

`compose.yaml` 提供 postgres、redis、django、celery、centrifugo。
`compose.web.yaml` 在此之上：

- 改 `django` / `centrifugo` 端口映射与对外地址
- 把原 `celery` 收窄为只吃 `critical`（避免与 worker-default 重复消费）
- 新增 `worker-default` / `worker-realtime` / `worker-search` / `worker-data-ai`
  / `worker-heavy` / `worker-ai-background` / `worker-tracker`
- 新增 `beat`（单实例）
- 新增 `collab-live`、`tabtin-web`、`admindash`

8 类 worker 的队列与并发严格对齐 `tabtin/runtime/registry.py` 的
`WORKER_REGISTRY`，合计覆盖 `QUEUE_REGISTRY` 全部 14 个队列，每个队列恰好一个
消费者。**改动队列划分时必须同步改注册表**。

## 关键约束

三处是读代码得出的硬约束，不是可调偏好。

**`DEBUG=True` 是本形态唯一可行取值。** 沿用 `compose.yaml` 既定做法。三条相互
牵制：`apps/services/oss/services/factory.py:144` 在 `DEBUG=False` 时拒绝环回
的 local OSS 公开地址（我们用公网 IP，这条能过）；`settings.py:2275` 在
`DEBUG=False` 且 `ENABLE_HTTPS_SECURITY=true` 时开 `SECURE_SSL_REDIRECT`，纯
HTTP 下变 301 死循环，故必须 `ENABLE_HTTPS_SECURITY=false`；邀请链接见下。

**邀请链接在公网 IP + HTTP 下不可用。**
`apps/tabtinspace/services/invitation_service.py:113-129` 要求
`PUBLIC_WEB_BASE_URL` 必须是 HTTPS，或是私有网段 / localhost 的 HTTP。公网 IP
走 HTTP 两条都不满足，调用即抛 `ImproperlyConfigured`（HTTP 500）。这是代码写死
的策略，本形态未改代码绕过。其余功能正常。解法是切 HTTPS 域名。

**Centrifugo 的 `allowed_origins` 必须换。**
`community-assets/centrifugo.template.json` 把它写死成 `localhost:5175`
（Electron 渲染进程），而 `community_secrets.py:_render_centrifugo_config()` 只
替换三个 `__CENTRIFUGO_*__` 密钥占位符、不碰 origins。照原样部署，13490 的 WS
握手会被 Centrifugo 直接拒绝。

因此本形态用 `community-assets/centrifugo.web.template.json.in` 作为源文件，
`web-up.sh` 把 `__SERVER_ORIGINS__` 替换成 13490/13491 后生成同名 `.json`
（gitignored），再经 compose 挂载进容器，并用已存在的
`TABTIN_COMMUNITY_CENTRIFUGO_TEMPLATE` 变量指过去。**未改任何 Python 代码。**

新模板相比原模板只差 origins：去掉了 Electron 的 `tabtin-file://app`。若之后要
让桌面客户端也连这台服务器，把该 origin 加回 `.in` 源文件即可。

### 构建 tabtin-web 时会打印一条警告，属正常现象

```
[tabtin-config] Ignoring invalid public invite web base URL:
Public invite links must use HTTPS web URLs outside localhost or a private LAN
```

`apps/tabtin-web/vite.config.ts:76` 在配置加载期（含 build）调
`resolveApiRuntimeConfig`，其中 `resolvePublicWebBaseUrl` 对公网 IP + HTTP 的
`VITE_PUBLIC_WEB_BASE_URL` 会抛错 —— 但 `packages/tabtin-config/src/index.ts:198`
把它 catch 住只打 warning 并返回 undefined，**不会中断构建**。

admindash 不受影响：它那处调用被 `if (command === 'serve')` 包着，只在 dev 跑。

顺带说明邀请链接这条限制是**三层独立实施**的，只改一处没用：

| 层 | 位置 |
|---|---|
| Django 服务 | `invitation_service.py:113-129`（有测试 `test_..._rejects_public_http` 断言） |
| 共享配置包 | `packages/tabtin-config/src/index.ts:76-92` `normalizePublicInviteWebBaseUrl` |
| 前端调用点 | `apps/tabtin-web/src/config/api.ts:92` `buildPublicInviteUrl` |

## 前端地址是构建期烧进镜像的

Vite 在 `vite build` 时把 `import.meta.env.VITE_*` 内联进 bundle，**改容器环境
变量无效**。换 IP 或换域名必须重新 build `tabtin-web` 与 `admindash`：

```bash
SERVER_IP=<新IP> bash scripts/community/web-up.sh   # 会重新 build
```

tabtin-web 另有运行时兜底（`public/runtime-env.js` →
`window.__TABTIN_RUNTIME_CONFIG__`，见 `src/config/api.ts:15-27`），admindash
没有（`src/api/client.ts:68` 只读 `import.meta.env`）。

## 生成的文件

| 文件 | 由谁生成 | 是否进 git |
|---|---|---|
| `.env.community-runtime` | `ensure-env-file.sh` | 否 |
| `.env.web-runtime`（存 `COLLAB_LIVE_SECRET`） | `web-up.sh` | 否 |
| `community-assets/centrifugo.web.template.json` | `web-up.sh` | 否 |

`COLLAB_LIVE_SECRET` 持久化在 `.env.web-runtime`，是 Django ↔ collab-live 的
`X-Live-Secret` 双向鉴权凭据，两侧必须同值。删掉该文件会重新生成新值，此时必须
整栈重启，不能只重启单侧。

### secret 注入机制（secret-by-env-file）

`compose.web.yaml` 通过各服务的 `env_file: ./.env.web-runtime` 直接从文件读取
`COLLAB_LIVE_SECRET`（django / celery / x-worker-common 派生的 8 类 worker +
beat / collab-live）。**不依赖 compose 命令调用方先 `export`**。

历史教训：旧实现用 `${COLLAB_LIVE_SECRET}` 环境变量插值，重建容器时忘了先
`source .env.web-runtime` 就会静默把空字符串传进 django —— django 照常启动，
但拒绝所有内部服务请求（collab-live 拉文档快照 403），客户端表现为
"协作同步·连接中"永远转圈。该事故 2026-09-10 一天内发生两次（13:21 与 21:40
两轮重建均中招），故改为 env_file 显式声明。

当前行为：

- 裸 `docker compose -f compose.yaml -f compose.web.yaml up -d` 也能拿到正确
  secret（`env_file` 优先级低于 `environment`，不影响 `web-up.sh` 的 export 路径）
- `.env.web-runtime` 文件不存在时，compose 直接报错 fail-fast，不会带空 secret
  静默运行
- `SERVER_IP` 的 `${...}` 插值仍来自环境变量或根 `.env`；服务器根 `.env` 已加
  `SERVER_IP=` 兜底行，裸命令下 `ALLOWED_HOSTS` / `CORS_ALLOWED_ORIGINS` 等
  不会渲染成空值（换服务器 IP 时记得同步改该行）

## 部署后验证

`web-up.sh` 已自动做完第 1~2 步。其余需要手工执行。

```bash
cd <repo> && export SERVER_IP=<你的公网IP>
dc() { docker compose -f compose.yaml -f compose.web.yaml "$@"; }
```

**1. 容器状态** —— 14 个服务 running，带健康检查的为 healthy（beat 无健康检查）。

```bash
dc ps
```

**2. 五个端口连通**

```bash
curl -sf http://$SERVER_IP:13492/health/ready && echo django-ok
curl -sf http://$SERVER_IP:13493/health       && echo collab-ok
curl -sf http://$SERVER_IP:13494/health       && echo centrifugo-ok
curl -sI http://$SERVER_IP:13490/ | head -1
curl -sI http://$SERVER_IP:13491/ | head -1
```

**3. SPA 深链 fallback** —— 都必须 200，返回 404 说明 `try_files` 没生效。

```bash
curl -sI http://$SERVER_IP:13490/shared/docs/nonexistent | head -1
curl -sI http://$SERVER_IP:13491/monitoring/queues       | head -1
```

**4. 前端地址真的内联进包了** —— 无输出说明 build args 没传进去，前端会打到
错误地址。

```bash
dc exec tabtin-web grep -rlo "$SERVER_IP:13492" /usr/share/nginx/html/assets/ | head -1
dc exec admindash  grep -rlo "$SERVER_IP:13492" /usr/share/nginx/html/assets/ | head -1
```

**5. 14 个队列全部有消费者（最关键）** —— 逐一核对 `QUEUE_REGISTRY` 的队列名，
特别确认 `tracker_agent` 没有派生后缀。

```bash
dc exec worker-default celery -A tabtin inspect active_queues
```

**6. beat 在调度且严格单实例**

```bash
dc logs beat | tail -30     # 应见 DatabaseScheduler 起来
dc ps beat                  # 必须恰好 1 个
```

**7. 浏览器端到端**（curl 替代不了，必须实际打开）

- 开 `http://SERVER_IP:13490` 登录，DevTools Network 确认 XHR 打到 13492 且
  **无 CORS 报错**
- 两个浏览器窗口同开一张表，编辑一格，另一窗口应实时同步 —— 验证 collab-live
  闭环（WS 连 13493 `/table-collaboration`）
- 确认 Centrifugo WS 连上 13494 且**没有 origin 被拒** —— 验证 web 模板生效
- 上传一张图片后重新加载，确认能显示 —— 验证 local OSS 的
  `TABTIN_PUBLIC_BASE_URL` 正确
- 开 `http://SERVER_IP:13491` 登录管理台

**8. 确认数据库没被意外暴露** —— 前两条应报错/无输出，第三条不应有匹配。

```bash
dc port postgres 5432
dc port redis 6379
ss -tlnp | grep -E '5432|6379'
```

**9. 重启幂等** —— 密钥与数据卷应复用，不重新生成、不丢数据。

```bash
dc down && SERVER_IP=$SERVER_IP bash scripts/community/web-up.sh
```

**10. 裸命令重建不丢 secret**（secret-by-env-file 回归测试）—— 不 source
任何文件、不 export 任何变量，直接重建 django 侧服务后，secret 必须仍在：

```bash
docker compose -f compose.yaml -f compose.web.yaml up -d --force-recreate django
docker compose -f compose.yaml -f compose.web.yaml exec django \
  sh -c 'test -n "$COLLAB_LIVE_SECRET" && echo secret-ok || echo SECRET-LOST'
```

期望输出 `secret-ok`。若输出 `SECRET-LOST`，检查 `.env.web-runtime` 是否存在
且非空、是否被 compose 的 `env_file` 声明引用。

## 已知限制

1. **邀请链接不可用** —— 见上「关键约束」。切 HTTPS 域名可解。
2. **`DEBUG=True`** —— 报错页暴露堆栈。这是 dogfood / 内网试用形态，不是面向
   公网用户的生产加固形态。
3. **前端地址烧进镜像** —— 换 IP / 换域名必须重新 build。
4. **collab-live 镜像含 devDependencies** —— 为构建确定性选择整树 COPY 而非
   `pnpm deploy --prod`（见 `apps/collab-live/Dockerfile` 内注释）。在服务器上
   验证过 `pnpm deploy` 后可以瘦身。
5. **前端镜像跳过 `tsc` 类型检查** —— 那是 `noEmit` 纯检查、不产出物，属于 CI
   职责；不让一个类型错误卡住部署构建。
6. **未纳入**：`run_longpoll`（微信 iLink 等轮询型渠道不可用）、Elasticsearch
   全文检索（`SEARCH_ENGINE_ENABLED=false`，`search_indexing` 队列有 worker 但
   无引擎）、tabtin-daemon(6080)、官网(8765)。
7. **单机形态** —— worker 均单副本；beat 必须保持单实例，多副本会重复触发定时
   任务。

## 后续切 HTTPS 域名

只动配置，不动镜像结构：`compose.web.yaml` 里 `http://${SERVER_IP}:134xx` 换成
`https://<域名>`（外层 TLS 终止后回源）、`DEBUG` 置 `False`、
`ENABLE_HTTPS_SECURITY=true`（`SECURE_PROXY_SSL_HEADER` 已在
`settings.py:2281` 就绪）、重新 build 两个前端镜像。届时邀请链接与
`DEBUG=True` 两个限制同时解除。

> AI生成