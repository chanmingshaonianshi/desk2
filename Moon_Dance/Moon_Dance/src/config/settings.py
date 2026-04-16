#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局配置管理模块
功能：统一管理项目所有配置常量、环境变量读取、路径配置
作用：集中配置避免硬编码，支持开发/生产环境差异化配置
使用原因：所有模块都从这里读取配置，修改一处全局生效，便于维护
"""
import os
import sys

# 获取应用根目录
if getattr(sys, 'frozen', False):
    # 如果是打包后的 exe 运行，使用 exe 所在的目录
    BASE_PATH = os.path.dirname(os.path.abspath(sys.executable))
else:
    # 如果是 python 脚本运行
    # 获取 main.py 所在的目录 (即 Moon_Dance 目录)
    # 当前文件在 src/config/settings.py -> 上3级目录
    BASE_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 确保 BASE_PATH 存在 (理论上一定存在，但为了稳健性)
if not os.path.exists(BASE_PATH):
    BASE_PATH = os.getcwd()

# 数据/日志目录移到Moon_Dance外层，与代码分离
PROJECT_ROOT = os.path.dirname(BASE_PATH)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
REALTIME_LOG_DIR = os.path.join(DATA_DIR, "realtime_logs")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
TEMP_DIR = os.path.join(PROJECT_ROOT, "tmp")

# 自动创建目录
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(REALTIME_LOG_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

print(f"DEBUG: App Root Path (BASE_PATH) = {BASE_PATH}")
print(f"DEBUG: Data Path = {DATA_DIR}")
print(f"DEBUG: Log Path = {LOG_DIR}")

CERT_DIR = "certs"
CERT_FILE = "server.crt"
KEY_FILE = "server.key"
CA_CERT_FILE = "ca.crt"
CA_KEY_FILE = "ca.key"

API_APP_ID = os.environ.get("API_APP_ID", "moon_dance_app")
API_APP_SECRET = os.environ.get("API_APP_SECRET", "moon_dance_secret")
API_KEY = os.environ.get("API_KEY", "myh")
JWT_SECRET = os.environ.get("JWT_SECRET", "moon_dance_change_me_please_set_env_32bytes")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_SECONDS = int(os.environ.get("JWT_EXPIRE_SECONDS", "3600"))
PAYLOAD_ENCRYPTION_KEY = os.environ.get("PAYLOAD_ENCRYPTION_KEY", "f8SxB5xMZyCjV2kI4uJ2T0-G9R3gU4L8M-5I0K2oBqc=")

# Redis配置
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# 生产环境安全校验
if os.environ.get("ENV") == "production" and JWT_SECRET == "moon_dance_change_me_please_set_env_32bytes":
    raise ValueError("生产环境必须设置JWT_SECRET环境变量，禁止使用默认值！")

PROCESSED_IDS_FILE = os.path.join(REALTIME_LOG_DIR, "processed_ids.json")
UPLOAD_LOG_FILE = os.path.join(REALTIME_LOG_DIR, "upload_log.jsonl")
UPLOAD_REPORT_DIR = os.path.join(REPORTS_DIR, "uploads")

# 设备颜色配置
DEVICE_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
]

# 窗口配置
WINDOW_TITLE = "坐垫压力监测系统 (Canvas 曲线版)"
WINDOW_SIZE = "800x900"
WINDOW_BG = "#f0f2f5"

# 评估阈值
RATIO_NORMAL = 0.05
RATIO_WARNING = 0.10

# 图表配置
CHART_WINDOW_SIZE = "900x650"
CHART_TITLE_FONT = ("微软雅黑", 16, "bold")
CHART_AXIS_FONT = ("Arial", 9)
CHART_HOUR_RANGE = list(range(8, 25))
CHART_MAX_RATIO = 40  # Y轴最大值40%
