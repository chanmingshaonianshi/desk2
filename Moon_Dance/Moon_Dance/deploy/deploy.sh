#!/bin/bash

set -euo pipefail

# =======================================================
# 文件：deploy.sh
# 实现了什么：服务器一键部署脚本。
# 默认模式：git pull 后直接重建 api/worker/nginx 容器，不重新 build 镜像。
# 重建模式：bash deploy.sh --rebuild，会关闭 BuildKit 并重新构建 api/worker 镜像。
# 为什么这样做：当前 compose 已挂载宿主机源码到容器，日常 Python 代码更新不必重新构建镜像；
# 只有 Dockerfile / requirements.txt / docker-compose.yml 变化时才需要完整重建。
# =======================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$APP_DIR/.." && pwd)"
REBUILD_MODE="${1:-}"

echo "======================================================="
echo " [1/4] 清理服务器运行时文件并拉取最新代码..."
echo "======================================================="
cd "$REPO_ROOT"

# 这些文件/目录是服务运行时产生的，不能阻塞 git pull
git restore --staged Moon_Dance/data/realtime_logs/realtime_log.jsonl 2>/dev/null || true
git restore Moon_Dance/data/realtime_logs/realtime_log.jsonl 2>/dev/null || true
git restore --staged Moon_Dance/data/history_data.json 2>/dev/null || true
git restore Moon_Dance/data/history_data.json 2>/dev/null || true
git clean -fd -- \
  Moon_Dance/data/reports \
  Moon_Dance/logs \
  Moon_Dance/tmp \
  data/realtime_logs \
  logs \
  tmp 2>/dev/null || true

git pull origin main

echo ""
echo "======================================================="
echo " [2/4] 进入部署目录并准备更新服务..."
echo "======================================================="
cd "$SCRIPT_DIR"

if [[ "$REBUILD_MODE" == "--rebuild" ]]; then
  echo ""
  echo "======================================================="
  echo " [3/4] 完整重建镜像（关闭 BuildKit，避免元数据拉取失败）..."
  echo "======================================================="
  export DOCKER_BUILDKIT=0
  export COMPOSE_DOCKER_CLI_BUILD=0
  docker compose build api worker

  echo ""
  echo "======================================================="
  echo " [4/4] 启动最新服务集群..."
  echo "======================================================="
  docker compose up -d api worker nginx
else
  echo ""
  echo "======================================================="
  echo " [3/4] 快速部署：复用现有镜像并强制重建容器..."
  echo "======================================================="
  docker compose up -d --no-build --force-recreate api worker nginx

  echo ""
  echo "======================================================="
  echo " [4/4] 验证服务状态..."
  echo "======================================================="
fi

docker compose ps
echo ""
echo "[健康检查] http://127.0.0.1:8000/health"
curl -fsS http://127.0.0.1:8000/health || true
echo ""
echo "======================================================="
echo " ✅ 部署完成。"
echo " 默认使用: bash deploy.sh"
echo " 依赖变更时: bash deploy.sh --rebuild"
echo "======================================================="
