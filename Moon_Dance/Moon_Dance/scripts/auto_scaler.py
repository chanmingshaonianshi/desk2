#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_scaler.py — 自动扩缩容启动入口（scripts/ 目录快捷入口）

核心逻辑已迁移至 src/core/dynamic_scaler.py，
本文件仅保留启动入口，方便从 scripts/ 目录直接运行。
"""

import os
import sys

# 将项目根目录加入 sys.path，使 src.core 包可被正确导入
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.dynamic_scaler import monitor_and_scale  # noqa: E402


if __name__ == "__main__":
    monitor_and_scale()
