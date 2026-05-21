#!/bin/bash

set -euo pipefail

# =======================================================
# 文件：deploy.sh
# 实现了什么：服务器强制同步最新代码、保住正式证书、清理旧容器并完成一键重建部署。
# 怎么实现的：先备份服务器本机证书，再中止残留 merge/rebase，随后 fetch + reset 到 origin/main；
#           然后恢复正式证书、移除会抢占 80/443/8000 端口的旧容器，最后执行 docker compose down/build/up。
# 为什么实现：服务器上常有运行时文件修改与历史冲突状态，直接 git pull 容易失败；此脚本专门为云服务器场景做了兜底。
# =======================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CERT_DIR="$REPO_ROOT/certs"
BACKUP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$BACKUP_DIR"
}

trap cleanup EXIT

backup_cert() {
  local source_path="$1"
  local backup_name="$2"
  if [ -f "$source_path" ]; then
    cp "$source_path" "$BACKUP_DIR/$backup_name"
  fi
}

restore_cert() {
  local backup_name="$1"
  local target_path="$2"
  if [ -f "$BACKUP_DIR/$backup_name" ]; then
    mkdir -p "$(dirname "$target_path")"
    cp "$BACKUP_DIR/$backup_name" "$target_path"
  fi
}

# 切换到脚本所在目录，确保 docker compose 命令能找到 yml 文件
cd "$SCRIPT_DIR"

echo "======================================================="
echo " [1/5] 正在备份服务器正式证书..."
echo "======================================================="
backup_cert "$CERT_DIR/server.crt" "server.crt"
backup_cert "$CERT_DIR/server.key" "server.key"
backup_cert "$HOME/server.crt" "server.crt"
backup_cert "$HOME/server.key" "server.key"

echo ""
echo "======================================================="
echo " [2/5] 正在强制同步 GitHub 最新代码..."
echo "======================================================="
cd "$REPO_ROOT"
git merge --abort 2>/dev/null || true
git rebase --abort 2>/dev/null || true
git cherry-pick --abort 2>/dev/null || true
git fetch origin main
git reset --hard origin/main

echo ""
echo "======================================================="
echo " [3/5] 正在恢复正式证书并清理旧容器..."
echo "======================================================="
restore_cert "server.crt" "$CERT_DIR/server.crt"
restore_cert "server.key" "$CERT_DIR/server.key"
if [ -f "$CERT_DIR/server.key" ]; then
  chmod 600 "$CERT_DIR/server.key"
fi
docker rm -f nginx-ssl moondance-api >/dev/null 2>&1 || true
cd "$SCRIPT_DIR"

echo ""
echo "======================================================="
echo " [4/5] 正在安全停止当前运行的后端集群..."
echo "======================================================="
docker compose down

echo ""
echo "======================================================="
echo " [5/5] 正在重新构建并启动全新集群..."
echo "======================================================="
docker compose build
docker compose up -d --force-recreate

echo ""
echo "======================================================="
echo " ✅ 部署完成！服务器已同步到 GitHub 最新版本。"
echo " 已自动保留证书，并重建当前 Docker 集群。"
echo "======================================================="
docker compose ps
