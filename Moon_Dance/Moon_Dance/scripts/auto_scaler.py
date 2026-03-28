#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动扩缩容脚本 (Auto-scaling Script)
功能：根据Redis消息队列长度自动扩展或缩减Docker容器实例数量
适用场景：项目验收“优”标准 - 面向消息队列构建服务器集群，可根据访问量启停docker服务
运行环境：部署有Docker环境的宿主机（服务器端）
"""

import os
import time
import subprocess
import redis

# 部署目录路径，确保 docker compose 命令在此目录下执行
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPLOY_DIR = os.path.join(BASE_DIR, 'deploy')

# Redis 配置 (默认连接本地docker映射的Redis)
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
CELERY_QUEUE_NAME = 'celery'  # Celery默认队列名称

# 扩缩容策略配置
CHECK_INTERVAL = 10  # 检查间隔（秒）
MIN_WORKERS = 1      # 最小Worker容器数量
MAX_WORKERS = 5      # 最大Worker容器数量

# 阈值配置
SCALE_UP_THRESHOLD = 50   # 队列长度大于该值时，扩容
SCALE_DOWN_THRESHOLD = 10 # 队列长度小于该值时，缩容

# 每次扩缩容的步长
SCALE_STEP = 1

def get_current_workers():
    """获取当前运行的worker容器数量"""
    try:
        # 获取 worker 容器数量，需要指定 compose 文件并在 deploy 目录下执行
        result = subprocess.run(
            ['docker', 'compose', '-f', 'docker-compose.yml', '-f', 'docker-compose-nginx.yml', 'ps', '-q', 'worker'],
            cwd=DEPLOY_DIR,
            capture_output=True, text=True, check=True
        )
        # 每行一个容器ID，统计非空行数
        return len([line for line in result.stdout.split('\n') if line.strip()])
    except subprocess.CalledProcessError as e:
        print(f"获取Worker数量失败: {e}")
        return MIN_WORKERS
    except FileNotFoundError:
        print("未找到docker命令，请确保在服务器宿主机运行该脚本。")
        return MIN_WORKERS

def scale_workers(target_count):
    """执行Docker Compose扩缩容命令"""
    print(f"🚀 正在将 worker 容器数量调整为: {target_count}")
    try:
        # 使用 docker compose up -d --scale worker=N，需要在 deploy 目录下执行
        subprocess.run(
            ['docker', 'compose', '-f', 'docker-compose.yml', '-f', 'docker-compose-nginx.yml', 'up', '-d', '--scale', f'worker={target_count}', '--no-recreate'],
            cwd=DEPLOY_DIR,
            check=True
        )
        print(f"✅ 扩缩容完成，当前 worker 数量: {target_count}")
    except subprocess.CalledProcessError as e:
        print(f"❌ 扩缩容失败: {e}")

def monitor_and_scale():
    """主监控逻辑"""
    print(f"🔍 开始监控Redis队列: {CELERY_QUEUE_NAME} (目标Redis: {REDIS_HOST}:{REDIS_PORT})")
    print(f"⚙️  扩容阈值: >{SCALE_UP_THRESHOLD} | 缩容阈值: <{SCALE_DOWN_THRESHOLD}")
    print(f"⚙️  Worker数量范围: {MIN_WORKERS} ~ {MAX_WORKERS}")
    
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    
    current_workers = get_current_workers()
    print(f"📊 初始Worker数量: {current_workers}")
    
    while True:
        try:
            # 获取队列长度
            queue_length = r.llen(CELERY_QUEUE_NAME)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 队列长度: {queue_length} | 当前Worker数: {current_workers}")
            
            # 扩容逻辑
            if queue_length > SCALE_UP_THRESHOLD and current_workers < MAX_WORKERS:
                new_workers = min(current_workers + SCALE_STEP, MAX_WORKERS)
                print(f"⚠️ 队列积压 ({queue_length} > {SCALE_UP_THRESHOLD})，准备扩容: {current_workers} -> {new_workers}")
                scale_workers(new_workers)
                current_workers = new_workers
                
            # 缩容逻辑
            elif queue_length < SCALE_DOWN_THRESHOLD and current_workers > MIN_WORKERS:
                new_workers = max(current_workers - SCALE_STEP, MIN_WORKERS)
                print(f"♻️ 负载较低 ({queue_length} < {SCALE_DOWN_THRESHOLD})，准备缩容: {current_workers} -> {new_workers}")
                scale_workers(new_workers)
                current_workers = new_workers
                
        except redis.ConnectionError:
            print(f"❌ 无法连接到Redis ({REDIS_HOST}:{REDIS_PORT})，请检查服务状态")
        except Exception as e:
            print(f"❌ 发生异常: {e}")
            
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    monitor_and_scale()
