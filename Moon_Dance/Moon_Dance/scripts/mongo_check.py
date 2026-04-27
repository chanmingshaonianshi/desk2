#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MongoDB 数据验证脚本
功能：一键查看 MongoDB 中各集合的数据量、最新原始数据、每日汇总结果、排行榜
使用方式：
    python3 scripts/mongo_check.py           # 查看全部信息
    python3 scripts/mongo_check.py --count    # 只看数据量统计
    python3 scripts/mongo_check.py --latest   # 只看最新原始数据
    python3 scripts/mongo_check.py --stats    # 只看每日汇总结果
    python3 scripts/mongo_check.py --rank     # 只看排行榜
"""

import os
import sys
import argparse

# 路径处理：确保从项目任意位置都能正确导入
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pymongo import MongoClient, DESCENDING
from src.utils.mongo_db import MONGO_URI, DB_NAME


def get_db():
    """获取数据库连接"""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    client.admin.command('ping')
    return client[DB_NAME]


def show_count(db):
    """显示各集合数据量"""
    print("\n========= MongoDB 数据量统计 =========")
    collections = {
        "pressure_data": "设备上报原始数据（主链路）",
        "daily_stats": "每日汇总统计",
        "users": "注册用户信息"
    }
    for col_name, desc in collections.items():
        count = db[col_name].count_documents({})
        print(f"  {col_name:20s} ({desc}): {count} 条")
    print("======================================\n")


def show_latest(db, limit=5):
    """显示最新几条原始设备数据"""
    print(f"\n===== 最新 {limit} 条原始设备数据 =====")
    col = db["pressure_data"]
    records = list(col.find().sort("_id", DESCENDING).limit(limit))
    if not records:
        print("  （暂无数据）")
    else:
        for i, d in enumerate(records, 1):
            dev = d.get("device_id", "未知")
            t = d.get("time", "未知")
            fl = d.get("f_left", 0)
            fr = d.get("f_right", 0)
            ratio = d.get("ratio", 0)
            print(f"  {i:02d}. [{t}] 设备:{dev} | 左:{fl:.1f}N 右:{fr:.1f}N | 偏差:{ratio:.2%}")
    print()


def show_daily_stats(db, limit=10):
    """显示每日汇总结果"""
    print(f"\n===== 每日汇总结果（最近 {limit} 条） =====")
    col = db["daily_stats"]
    records = list(col.find().sort("date", DESCENDING).limit(limit))
    if not records:
        print("  （暂无汇总数据，请先运行: python3 scripts/daily_aggregation.py --run-now）")
    else:
        for d in records:
            dt = d.get("date", "?")
            dev = d.get("device_id", "?")
            mins = d.get("total_seated_minutes", 0)
            bad = d.get("bad_posture_count", 0)
            score = d.get("health_score", 0)
            print(f"  日期:{dt} | 设备:{dev} | 入座:{mins}分钟 | 不良姿势:{bad}次 | 健康评分:{score}分")
    print()


def show_leaderboard(db, limit=10):
    """显示健康坐姿排行榜"""
    print(f"\n===== 健康坐姿排行榜 TOP {limit} =====" )
    col = db["daily_stats"]
    records = list(col.find().sort("health_score", DESCENDING).limit(limit))
    if not records:
        print("  （暂无排行数据，请先运行: python3 scripts/daily_aggregation.py --run-now）")
    else:
        for rank, d in enumerate(records, 1):
            dev = d.get("device_id", "?")
            score = d.get("health_score", 0)
            mins = d.get("total_seated_minutes", 0)
            date = d.get("date", "?")
            print(f"  第{rank}名: 设备 {dev} | 评分 {score} 分 | 入座 {mins} 分钟 | 日期 {date}")
    print()


def main():
    parser = argparse.ArgumentParser(description="MongoDB 数据验证工具")
    parser.add_argument("--count", action="store_true", help="只显示数据量统计")
    parser.add_argument("--latest", action="store_true", help="只显示最新原始数据")
    parser.add_argument("--stats", action="store_true", help="只显示每日汇总结果")
    parser.add_argument("--rank", action="store_true", help="只显示排行榜")
    parser.add_argument("--limit", type=int, default=10, help="显示条数（默认10）")
    args = parser.parse_args()

    # 如果没有指定任何参数，则显示全部
    show_all = not (args.count or args.latest or args.stats or args.rank)

    try:
        db = get_db()
        print("[OK] MongoDB 连接成功！")
    except Exception as e:
        print(f"[FAIL] MongoDB 连接失败: {e}")
        print("   请检查 MongoDB 是否在 27017 端口正常运行。")
        sys.exit(1)

    if show_all or args.count:
        show_count(db)
    if show_all or args.latest:
        show_latest(db, args.limit)
    if show_all or args.stats:
        show_daily_stats(db, args.limit)
    if show_all or args.rank:
        show_leaderboard(db, args.limit)


if __name__ == "__main__":
    main()
