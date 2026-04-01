#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQ服务模块管理脚本
功能：管理所有MQ工作节点的启动、停止、状态查看，支持多副本
使用方法：
  启动节点：python scripts/mq_manager.py start <模块名> [副本数]
  停止节点：python scripts/mq_manager.py stop <模块名/all>
  查看状态：python scripts/mq_manager.py status
支持的模块：validator, writer, logger
"""
import os
import sys
import time
import signal
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config.settings import TEMP_DIR, BASE_PATH

try:
    import psutil
except Exception:
    psutil = None

# 模块配置
MODULE_CONFIG = {
    "validator": {
        "module": "src.mq_workers.validator_worker",
        "name_prefix": "validator_worker_",
        "max_replicas": 10
    },
    "writer": {
        "module": "src.mq_workers.writer_worker",
        "name_prefix": "writer_worker_",
        "max_replicas": 10
    },
    "logger": {
        "module": "src.mq_workers.logger_worker",
        "name_prefix": "logger_worker",
        "max_replicas": 1
    }
}

PID_DIR = os.path.join(TEMP_DIR, "mq_pids")
os.makedirs(PID_DIR, exist_ok=True)

def get_pid_file(module_name, instance_id=1):
    """获取pid文件路径"""
    if module_name == "logger":
        return os.path.join(PID_DIR, f"logger.pid")
    return os.path.join(PID_DIR, f"{module_name}_{instance_id}.pid")

def save_pid(module_name, instance_id, pid):
    """保存进程pid到文件"""
    pid_file = get_pid_file(module_name, instance_id)
    with open(pid_file, 'w') as f:
        f.write(str(pid))

def load_pid(module_name, instance_id=1):
    """读取pid文件"""
    pid_file = get_pid_file(module_name, instance_id)
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                return int(f.read().strip())
        except:
            os.remove(pid_file)
    return None

def is_running(pid):
    """检查进程是否运行"""
    try:
        if psutil is not None:
            return psutil.pid_exists(pid) and psutil.Process(pid).is_running()
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def terminate_process(pid):
    """终止进程，优先使用 psutil，缺失时回退到标准库"""
    if psutil is not None:
        process = psutil.Process(pid)
        process.terminate()
        process.wait(timeout=3)
        return

    os.kill(pid, signal.SIGTERM)
    deadline = time.time() + 3
    while time.time() < deadline:
        if not is_running(pid):
            return
        time.sleep(0.1)
    raise TimeoutError(f"进程 {pid} 未在规定时间内退出")

def start_module(module_name, replicas=1):
    """启动指定模块的指定副本数"""
    if module_name not in MODULE_CONFIG:
        print(f"错误：未知模块 {module_name}，支持的模块：{list(MODULE_CONFIG.keys())}")
        return False
    
    config = MODULE_CONFIG[module_name]
    max_replicas = config["max_replicas"]
    
    if replicas > max_replicas:
        print(f"警告：{module_name} 最多支持 {max_replicas} 个副本，自动调整为 {max_replicas}")
        replicas = max_replicas
    
    # 统计当前运行的副本数
    running_count = 0
    for i in range(1, replicas + 1):
        pid = load_pid(module_name, i)
        if pid and is_running(pid):
            running_count += 1
        else:
            # 启动新副本
            cmd = [sys.executable, "-m", config["module"]]
            if module_name != "logger":
                cmd.append(str(i))
            
            # 后台启动
            if sys.platform == "win32":
                # Windows后台运行
                proc = subprocess.Popen(
                    cmd,
                    cwd=BASE_PATH,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                # Linux后台运行
                proc = subprocess.Popen(
                    cmd,
                    cwd=BASE_PATH,
                    preexec_fn=os.setpgrp,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            save_pid(module_name, i, proc.pid)
            print(f"已启动 {module_name} 副本 {i} (PID: {proc.pid})")
            time.sleep(0.5)
    
    print(f"\n{module_name} 启动完成：当前运行 {running_count + (replicas - running_count)} 个副本")
    return True

def stop_module(module_name):
    """停止指定模块的所有副本"""
    if module_name == "all":
        for mod in MODULE_CONFIG.keys():
            stop_module(mod)
        return True
    
    if module_name not in MODULE_CONFIG:
        print(f"错误：未知模块 {module_name}")
        return False
    
    config = MODULE_CONFIG[module_name]
    stopped_count = 0
    
    for i in range(1, config["max_replicas"] + 1):
        pid = load_pid(module_name, i)
        if pid and is_running(pid):
            try:
                terminate_process(pid)
                stopped_count += 1
                print(f"已停止 {module_name} 副本 {i} (PID: {pid})")
            except Exception as e:
                print(f"停止 {module_name} 副本 {i} 失败: {e}")
            finally:
                pid_file = get_pid_file(module_name, i)
                if os.path.exists(pid_file):
                    os.remove(pid_file)
    
    if stopped_count == 0:
        print(f"{module_name} 没有运行中的副本")
    else:
        print(f"已停止 {module_name} 的 {stopped_count} 个副本")
    return True

def show_status():
    """查看所有模块的运行状态"""
    print("="*70)
    print(f"{'模块名称':<15} {'副本ID':<8} {'PID':<8} {'状态':<10}")
    print("="*70)
    
    total_running = 0
    
    for module_name, config in MODULE_CONFIG.items():
        max_replicas = config["max_replicas"]
        for i in range(1, max_replicas + 1):
            pid = load_pid(module_name, i)
            status = "运行中" if pid and is_running(pid) else "已停止"
            if status == "运行中":
                total_running += 1
                print(f"{module_name:<15} {i:<8} {pid:<8} {status:<10}")
            # 只显示运行中的，logger只有一个副本
            if module_name == "logger":
                break
    
    print("="*70)
    print(f"总运行节点数: {total_running}")
    print("="*70)
    return True

def print_help():
    """打印帮助信息"""
    print("MQ服务模块管理脚本使用说明:")
    print("  启动节点: python scripts/mq_manager.py start <模块名> [副本数]")
    print("  停止节点: python scripts/mq_manager.py stop <模块名/all>")
    print("  查看状态: python scripts/mq_manager.py status")
    print("支持的模块: validator(数据验证), writer(数据写入), logger(日志统计)")
    print("示例:")
    print("  python scripts/mq_manager.py start validator 3  # 启动3个验证节点")
    print("  python scripts/mq_manager.py start writer 2     # 启动2个写入节点")
    print("  python scripts/mq_manager.py start logger      # 启动日志统计节点")
    print("  python scripts/mq_manager.py status            # 查看所有节点状态")
    print("  python scripts/mq_manager.py stop all          # 停止所有节点")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "start":
        if len(sys.argv) < 3:
            print("错误：请指定要启动的模块名")
            print_help()
            sys.exit(1)
        module_name = sys.argv[2].lower()
        replicas = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        start_module(module_name, replicas)
    elif command == "stop":
        if len(sys.argv) < 3:
            print("错误：请指定要停止的模块名或all")
            print_help()
            sys.exit(1)
        module_name = sys.argv[2].lower()
        stop_module(module_name)
    elif command == "status":
        show_status()
    else:
        print(f"错误：未知命令 {command}")
        print_help()
        sys.exit(1)
