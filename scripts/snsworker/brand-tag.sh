#!/usr/bin/env bash
# SnSworker 品牌化辅助脚本（fork 维护专用，零上游冲突）
#
# 作用：compose 体系已直接使用 snsworker/* 镜像名；本脚本负责兜底——
#   1) 若本机存在旧命名的 tabtin/* 镜像（上游代码或旧版本构建产物），
#      为它们补打 snsworker/* 别名 tag（同一 layer，不占额外磁盘）；
#   2) 输出当前镜像清单，方便部署时肉眼核对。
#
# 使用：
#   bash scripts/snsworker/brand-tag.sh          # 服务器部署后跑一次
#   bash scripts/snsworker/brand-tag.sh --list   # 只看清单，不打 tag
#
# 设计原则：
#   - 只加 tag、绝不删任何镜像（安全）；
#   - 独立目录 scripts/snsworker/，上游仓库不会有同名文件，merge 零冲突；
#   - 不修改任何上游代码。

set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"

# 上游镜像名 → 品牌名映射（新增镜像时往这里加一行即可）
declare -A MAPPING=(
  ["tabtin/community-django"]="snsworker/community-django"
  ["tabtin/tabtin-web"]="snsworker/web"
  ["tabtin/admindash"]="snsworker/admindash"
  ["tabtin/collab-live"]="snsworker/collab-live"
)

list_only=false
[[ "${1:-}" == "--list" ]] && list_only=true

command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found" >&2; exit 1; }

echo "== SnSworker 镜像别名管理（repo: ${repo_root##*/}）=="

tagged=0
for src in "${!MAPPING[@]}"; do
  dst="${MAPPING[$src]}"
  # 找本地所有该 repo 的 tag（含 :local / :dev 等任意 tag）
  tags=$(docker images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null \
    | grep -E "^${src}:" || true)
  if [[ -z "${tags}" ]]; then
    continue
  fi
  while IFS= read -r t; do
    tag_name="${t##*:}"
    target="${dst}:${tag_name}"
    if ${list_only}; then
      echo "[list] ${t} -> ${target}"
      continue
    fi
    if docker image inspect "${target}" >/dev/null 2>&1; then
      echo "[skip] ${target} 已存在"
    else
      docker tag "${t}" "${target}"
      echo "[tag ] ${t} -> ${target}"
      tagged=$((tagged + 1))
    fi
  done <<< "${tags}"
done

if ${list_only}; then
  echo "== 仅列出模式，未做任何修改 =="
else
  echo "== 完成：新打 ${tagged} 个别名 tag =="
fi

# 展示当前 snsworker/* 清单
echo
echo "== 当前 snsworker/* 镜像 =="
docker images --format '{{.Repository}}:{{.Tag}}\t{{.Size}}' 2>/dev/null \
  | grep '^snsworker/' || echo "(无)"
