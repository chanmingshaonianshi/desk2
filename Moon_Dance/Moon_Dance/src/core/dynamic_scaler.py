#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
模块名称：dynamic_scaler.py
所在路径：src/core/dynamic_scaler.py
=============================================================================

【功能概述】
    MoonDance 分布式服务的 Docker Worker 动态扩缩容核心模块。
    持续监控两个负载指标，根据阈值自动调整 docker compose 中
    Celery worker 容器的副本数，实现"既能起、又能停"的弹性伸缩。

【触发扩缩容的双指标】

    指标①  QPS（每秒请求速率）
        - 计算方式：读取 Redis 中 Celery 任务元数据键（celery-task-meta-*），
                    统计最近 QPS_WINDOW_SECONDS 秒内完成的任务数，换算为 QPS。
        - 扩容触发：QPS >= SCALE_UP_QPS_THRESHOLD（默认 5 req/s）
        - 缩容触发：QPS <  SCALE_DOWN_QPS_THRESHOLD（默认 1 req/s）

    指标②  Redis Stream 消息积压量（upstream_data 队列未消费消息数）
        - 计算方式：xlen("upstream_data") 返回 Stream 中总消息条数。
        - 扩容触发：积压量 >= SCALE_UP_BACKLOG_THRESHOLD（默认 100 条）
        - 缩容触发：积压量 <  SCALE_DOWN_BACKLOG_THRESHOLD（默认 20 条）

    最终决策：两个指标任一触发扩容 → 扩容；两个指标同时满足缩容 → 缩容。

【扩缩容参数】
    MIN_WORKERS             = 1        最少保留的 Worker 容器数
    MAX_WORKERS             = 5        最多允许的 Worker 容器数
    SCALE_STEP              = 1        每次扩/缩容的步长（容器数）
    SCALE_DOWN_COOLDOWN     = 30       缩容冷却时间（秒），避免频繁缩容
    CONSECUTIVE_DOWN_COUNT  = 3        连续满足缩容条件几轮后才真正缩容
    CHECK_INTERVAL          = 5        指标采集间隔（秒）

【依赖项】
    - redis>=4.0          (pip install redis)
    - docker compose v2   (宿主机需安装 Docker Desktop 或 Docker Engine + Compose 插件)
    - Python >= 3.9

【运行方式】
    # 直接运行（推荐在服务器宿主机执行）
    python -m src.core.dynamic_scaler

    # 或通过脚本入口
    python scripts/auto_scaler.py

【注意事项】
    - 本模块需要在能执行 docker compose 命令的宿主机上运行，不能在容器内运行。
    - 需要能访问 Redis 实例（默认 localhost:6379）。
    - DEPLOY_DIR 指向项目的 deploy/ 文件夹（含 docker-compose.yml）。
=============================================================================
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# 路径解析（支持从任意工作目录运行）
# ---------------------------------------------------------------------------
_THIS_FILE = os.path.abspath(__file__)
# src/core/dynamic_scaler.py → 向上3级 = Moon_Dance/ 包根目录
_PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS_FILE)))
DEPLOY_DIR = os.path.join(_PACKAGE_ROOT, "deploy")

# ---------------------------------------------------------------------------
# Redis 连接配置（支持环境变量覆盖）
# ---------------------------------------------------------------------------
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB   = int(os.getenv("REDIS_DB", "0"))

# ---------------------------------------------------------------------------
# 扩缩容阈值与参数
# ---------------------------------------------------------------------------
# --- Worker 副本数边界 ---
MIN_WORKERS = int(os.getenv("MIN_WORKERS", "1"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "5"))
SCALE_STEP  = int(os.getenv("SCALE_STEP", "1"))

# --- 指标 ①：QPS 阈值 ---
QPS_WINDOW_SECONDS         = int(os.getenv("QPS_WINDOW_SECONDS", "20"))   # 统计窗口（秒）
SCALE_UP_QPS_THRESHOLD     = float(os.getenv("SCALE_UP_QPS_THRESHOLD", "5.0"))   # QPS ≥ 此值 → 扩容
SCALE_DOWN_QPS_THRESHOLD   = float(os.getenv("SCALE_DOWN_QPS_THRESHOLD", "1.0")) # QPS < 此值 → 候选缩容

# --- 指标 ②：Redis Stream 积压量阈值 ---
UPSTREAM_STREAM_KEY               = os.getenv("UPSTREAM_STREAM_KEY", "upstream_data")
SCALE_UP_BACKLOG_THRESHOLD        = int(os.getenv("SCALE_UP_BACKLOG_THRESHOLD", "100"))  # 积压 ≥ 此值 → 扩容
SCALE_DOWN_BACKLOG_THRESHOLD      = int(os.getenv("SCALE_DOWN_BACKLOG_THRESHOLD", "20")) # 积压 < 此值 → 候选缩容

# --- 缩容稳定性控制 ---
SCALE_DOWN_COOLDOWN        = int(os.getenv("SCALE_DOWN_COOLDOWN", "30"))    # 缩容冷却秒数
CONSECUTIVE_DOWN_COUNT_REQ = int(os.getenv("CONSECUTIVE_DOWN_COUNT", "3"))  # 连续N轮才真正缩容

# --- 主循环间隔 ---
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "5"))


# ---------------------------------------------------------------------------
# 指标采集函数
# ---------------------------------------------------------------------------

def get_qps(r) -> float:
    """
    计算最近 QPS_WINDOW_SECONDS 秒内的任务完成速率（req/s）。
    """
    count = 0
    now = time.time()
    cutoff = now - QPS_WINDOW_SECONDS
    try:
        # 获取所有任务元数据键
        keys = r.keys("celery-task-meta-*")
        if not keys:
            return 0.0

        # 按时间倒序检查
        for key in reversed(keys[-1000:]):
            try:
                raw = r.get(key)
                if not raw:
                    continue
                task_info = json.loads(raw)
                date_done = task_info.get("date_done", "")
                if not date_done:
                    continue
                
                # 处理 ISO 格式时间戳
                dt_str = date_done.replace("+08:00", "").replace("+00:00", "").rstrip("Z")
                dt = datetime.fromisoformat(dt_str)
                if dt.tzinfo is None:
                    ts = dt.replace(tzinfo=timezone.utc).timestamp()
                else:
                    ts = dt.timestamp()
                
                if ts > cutoff:
                    count += 1
                elif ts < (cutoff - 60): # 如果已经落后窗口1分钟了，后面的肯定更旧
                    break
            except Exception:
                continue
    except Exception:
        pass

    return round(count / QPS_WINDOW_SECONDS, 2)


def get_stream_backlog(r) -> int:
    """
    获取 Redis Stream 真正的积压量 (Lag)。
    使用 XINFO GROUPS 查询 validator_group 的 lag。
    """
    try:
        groups = r.xinfo_groups(UPSTREAM_STREAM_KEY)
        for group in groups:
            if group.get('name') == b'validator_group' or group.get('name') == 'validator_group':
                # Redis 7.0+ 支持直接获取 lag 字段
                lag = group.get('lag')
                if lag is not None:
                    return int(lag)
                
                # 如果 Redis 版本较低不支持 lag，
                # 则估算: 积压 = Stream 总长度 - 最后交付的消息 ID 索引
                # 注意：这只是个近似值，但在大多数场景下足够精准
                pending = group.get('pending', 0)
                return int(pending)
        return 0
    except Exception:
        # 如果 Stream 还没创建，积压自然为 0
        return 0


def get_celery_queue_pending(r) -> int:
    """
    获取 Celery 队列中堆积的待处理任务数（辅助指标，用于日志展示）。

    :param r: redis.Redis 实例
    :return: 待处理任务数
    """
    total = 0
    for key in ["celery", "celery:default"]:
        try:
            key_type = r.type(key)
            if key_type == b"list":
                total += r.llen(key)
            elif key_type == b"zset":
                total += r.zcard(key)
        except Exception:
            pass
    return total


# ---------------------------------------------------------------------------
# Docker Compose 操作函数
# ---------------------------------------------------------------------------

def get_current_workers() -> int:
    """
    通过 docker compose ps -q worker 获取当前运行的 worker 容器数量。

    :return: 当前 worker 容器数，获取失败则返回 MIN_WORKERS
    """
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "-q", "worker"],
            cwd=DEPLOY_DIR,
            capture_output=True,
            text=True,
            timeout=10,
        )
        lines = [ln for ln in result.stdout.strip().split("\n") if ln.strip()]
        return len(lines) if lines else MIN_WORKERS
    except FileNotFoundError:
        print("[WARN] 未找到 docker 命令，请确保在宿主机运行且已安装 Docker。")
        return MIN_WORKERS
    except Exception as e:
        print(f"[WARN] 查询 Worker 数量失败: {e}")
        return MIN_WORKERS


def scale_workers(target: int) -> bool:
    """
    调用 docker compose up --scale 将 worker 副本数调整到 target。

    :param target: 目标 worker 副本数
    :return: 操作是否成功
    """
    print(f"  ▶ 正在调整 worker 副本数 → {target} ...", flush=True)
    try:
        subprocess.run(
            [
                "docker", "compose", "up", "-d",
                "--scale", f"worker={target}",
                "--no-recreate",
                "worker",
            ],
            cwd=DEPLOY_DIR,
            check=True,
            timeout=60,
        )
        print(f"  ✅ 副本数已调整为 {target}", flush=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ 扩缩容命令失败: {e}", flush=True)
        return False
    except Exception as e:
        print(f"  ❌ 扩缩容异常: {e}", flush=True)
        return False


# ---------------------------------------------------------------------------
# 主监控循环
# ---------------------------------------------------------------------------

def _print_banner():
    """打印启动信息横幅。"""
    print("=" * 62)
    print("  🚀  MoonDance 动态扩缩容监控  (dynamic_scaler.py)")
    print("=" * 62)
    print(f"  Redis        : {REDIS_HOST}:{REDIS_PORT}/db{REDIS_DB}")
    print(f"  Deploy 目录  : {DEPLOY_DIR}")
    print(f"  Worker 范围  : {MIN_WORKERS} ~ {MAX_WORKERS}  步长 {SCALE_STEP}")
    print(f"  采集间隔     : {CHECK_INTERVAL} 秒")
    print()
    print("  ── 扩容触发条件（任一满足）──────────────────────────")
    print(f"     QPS     ≥ {SCALE_UP_QPS_THRESHOLD} req/s")
    print(f"     积压量  ≥ {SCALE_UP_BACKLOG_THRESHOLD} 条")
    print()
    print("  ── 缩容触发条件（同时满足 + 稳定N轮 + 冷却）─────────")
    print(f"     QPS     < {SCALE_DOWN_QPS_THRESHOLD} req/s")
    print(f"     积压量  < {SCALE_DOWN_BACKLOG_THRESHOLD} 条")
    print(f"     连续    {CONSECUTIVE_DOWN_COUNT_REQ} 轮低负载")
    print(f"     冷却    {SCALE_DOWN_COOLDOWN} 秒")
    print("=" * 62)


def monitor_and_scale():
    """
    主监控循环：每隔 CHECK_INTERVAL 秒采集指标，按双指标策略做扩缩容决策。
    """
    _print_banner()

    # 连接 Redis
    try:
        import redis as redis_lib
        r = redis_lib.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
                            socket_connect_timeout=5, socket_timeout=5)
        r.ping()
        print(f"[OK] Redis 连接成功 ({REDIS_HOST}:{REDIS_PORT})")
    except Exception as e:
        print(f"[FAIL] Redis 连接失败: {e}")
        print("  请确认 Redis 服务运行中，或通过环境变量 REDIS_HOST/REDIS_PORT 指定地址。")
        sys.exit(1)

    current_workers = get_current_workers()
    print(f"[INFO] 当前 Worker 副本数: {current_workers}")
    print("=" * 62)
    print()

    last_scale_time: float = 0.0        # 上次扩缩容时刻
    consecutive_down: int = 0           # 连续满足缩容条件的轮次计数

    while True:
        try:
            qps     = get_qps(r)
            backlog = get_stream_backlog(r)
            pending = get_celery_queue_pending(r)
            ts      = time.strftime("%H:%M:%S")

            # ---- 决策逻辑 ------------------------------------------------
            should_scale_up   = (qps >= SCALE_UP_QPS_THRESHOLD) or \
                                 (backlog >= SCALE_UP_BACKLOG_THRESHOLD)
            candidate_down    = (qps <  SCALE_DOWN_QPS_THRESHOLD) and \
                                 (backlog < SCALE_DOWN_BACKLOG_THRESHOLD)

            # 更新缩容连续计数
            if candidate_down:
                consecutive_down += 1
            else:
                consecutive_down = 0

            cooldown_ok = (time.time() - last_scale_time) >= SCALE_DOWN_COOLDOWN
            should_scale_down = (
                candidate_down
                and consecutive_down >= CONSECUTIVE_DOWN_COUNT_REQ
                and cooldown_ok
                and current_workers > MIN_WORKERS
            )

            # ---- 执行扩缩容 -----------------------------------------------
            if should_scale_up and current_workers < MAX_WORKERS:
                new_workers = min(current_workers + SCALE_STEP, MAX_WORKERS)
                reason = []
                if qps >= SCALE_UP_QPS_THRESHOLD:
                    reason.append(f"QPS={qps}")
                if backlog >= SCALE_UP_BACKLOG_THRESHOLD:
                    reason.append(f"积压={backlog}")
                print(
                    f"\n[{ts}] ⬆️  SCALE UP  {current_workers} → {new_workers}"
                    f"  触发: {', '.join(reason)}"
                    f"  (待处理={pending})"
                )
                if scale_workers(new_workers):
                    current_workers = new_workers
                    last_scale_time = time.time()
                    consecutive_down = 0

            elif should_scale_down:
                new_workers = max(current_workers - SCALE_STEP, MIN_WORKERS)
                print(
                    f"\n[{ts}] ⬇️  SCALE DOWN  {current_workers} → {new_workers}"
                    f"  (QPS={qps}, 积压={backlog}, 连续{consecutive_down}轮低负载)"
                )
                if scale_workers(new_workers):
                    current_workers = new_workers
                    last_scale_time = time.time()
                    consecutive_down = 0

            else:
                # 正常状态：单行滚动输出
                down_hint = f" 缩容候选:{consecutive_down}/{CONSECUTIVE_DOWN_COUNT_REQ}" \
                            if candidate_down else ""
                status_line = (
                    f"[{ts}]  QPS={qps:5.2f}  积压={backlog:4d}"
                    f"  待处理={pending:3d}  Worker={current_workers}"
                    + down_hint
                )
                print(status_line, end="\r", flush=True)

        except KeyboardInterrupt:
            print("\n\n[INFO] 收到中断信号，监控退出。当前 Worker 副本数保持不变。")
            break
        except Exception as e:
            print(f"\n[ERROR] 监控循环异常: {e}", flush=True)

        time.sleep(CHECK_INTERVAL)


# ---------------------------------------------------------------------------
# 模块直接运行入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    monitor_and_scale()
