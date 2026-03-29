#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import subprocess
import time
from datetime import datetime

import redis

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEPLOY_DIR = os.path.join(BASE_DIR, "deploy")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

CHECK_INTERVAL = 3
MIN_WORKERS = 1
MAX_WORKERS = 5
SCALE_UP_THRESHOLD = 5
SCALE_DOWN_THRESHOLD = 2
SCALE_STEP = 1
SCALE_DOWN_COOLDOWN = 20
RECENT_TASKS_WINDOW = 10


def get_pending_tasks(r):
    count = 0
    for key in ["celery", "unacked", "unacked_index", "celery:default"]:
        try:
            key_type = r.type(key)
            if key_type == b"list":
                count += r.llen(key)
            elif key_type == b"set":
                count += r.scard(key)
            elif key_type == b"zset":
                count += r.zcard(key)
        except Exception:
            pass
    return count


def get_recent_task_throughput(r, window_seconds=10):
    count = 0
    cutoff_time = time.time() - window_seconds

    try:
        keys = r.keys("celery-task-meta-*")

        for key in keys[-300:]:
            try:
                data = r.get(key)
                if data:
                    task_info = json.loads(data)
                    date_done = task_info.get("date_done", "")
                    if date_done:
                        try:
                            dt_str = date_done.replace("+08:00", "").replace("+00:00", "")
                            dt = datetime.fromisoformat(dt_str)
                            task_timestamp = dt.timestamp()
                            if task_timestamp > cutoff_time:
                                count += 1
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception:
        pass

    return count


def get_current_workers():
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "-q", "worker"],
            cwd=DEPLOY_DIR,
            capture_output=True,
            text=True,
            check=True,
        )
        return len([line for line in result.stdout.split("\n") if line.strip()])
    except subprocess.CalledProcessError as e:
        print(f"获取Worker数量失败: {e}")
        return MIN_WORKERS
    except FileNotFoundError:
        print("未找到docker命令，请确保在服务器宿主机运行该脚本。")
        return MIN_WORKERS


def scale_workers(target_count):
    print(f"正在将 worker 容器数量调整为: {target_count}")
    try:
        subprocess.run(
            ["docker", "compose", "up", "-d", "--scale", f"worker={target_count}", "--no-recreate", "worker"],
            cwd=DEPLOY_DIR,
            check=True,
        )
        print(f"[OK] 扩缩容完成，当前 worker 数量: {target_count}")
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] 扩缩容失败: {e}")


def monitor_and_scale():
    print("=" * 55)
    print("  MoonDance 自动扩缩容监控")
    print("=" * 55)
    print(f"  扩容阈值: 吞吐量 > {SCALE_UP_THRESHOLD} 任务/{RECENT_TASKS_WINDOW}秒")
    print(f"  缩容阈值: 吞吐量 < {SCALE_DOWN_THRESHOLD} 任务/{RECENT_TASKS_WINDOW}秒")
    print(f"  Worker范围: {MIN_WORKERS} ~ {MAX_WORKERS}")
    print("=" * 55)

    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        r.ping()
        print("[OK] Redis连接成功")
    except Exception as e:
        print(f"[FAIL] Redis连接失败: {e}")
        return

    current_workers = get_current_workers()
    print(f"[INFO] 初始Worker数量: {current_workers}")
    print("=" * 55)

    last_scale_time = 0

    while True:
        try:
            pending = get_pending_tasks(r)
            throughput = get_recent_task_throughput(r, RECENT_TASKS_WINDOW)
            timestamp = time.strftime("%H:%M:%S")
            load_indicator = pending + throughput / 2
            status = f"[{timestamp}] 队列:{pending} | 吞吐:{throughput}/10s | 负载:{load_indicator:.1f} | Worker:{current_workers}"

            if load_indicator > SCALE_UP_THRESHOLD and current_workers < MAX_WORKERS:
                new_workers = min(current_workers + SCALE_STEP, MAX_WORKERS)
                print(f"\n{status}")
                print(f"[SCALE UP] 负载较高! 扩容: {current_workers} -> {new_workers}")
                scale_workers(new_workers)
                current_workers = new_workers
                last_scale_time = time.time()
            elif load_indicator < SCALE_DOWN_THRESHOLD and current_workers > MIN_WORKERS:
                if time.time() - last_scale_time > SCALE_DOWN_COOLDOWN:
                    new_workers = max(current_workers - SCALE_STEP, MIN_WORKERS)
                    print(f"\n{status}")
                    print(f"[SCALE DOWN] 负载较低，缩容: {current_workers} -> {new_workers}")
                    scale_workers(new_workers)
                    current_workers = new_workers
                    last_scale_time = time.time()
                else:
                    print(f"{status} (冷却中)", end="\r")
            else:
                print(status, end="\r")
        except redis.ConnectionError:
            print("\n[FAIL] Redis连接断开，尝试重连...")
            time.sleep(2)
        except Exception as e:
            print(f"\n[FAIL] 异常: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    monitor_and_scale()
