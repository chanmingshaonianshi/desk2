#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日数据汇总定时任务
功能：每天凌晨从 raw_device_data 中读取前一天的海量原始数据，
     按设备/用户聚合计算"总入座时长"、"不良坐姿次数"和"健康评分(0-100)"，
     将汇总结果写入 daily_stats 集合。
使用方式：
     方式1: 直接运行本文件，APScheduler 将在每天 00:05 自动执行
     方式2: 命令行传参 --run-now 立即手动执行一次（用于测试/补跑）
"""

import os
import sys
import argparse
from datetime import datetime, timedelta

# ============================================================
# 路径处理：确保从项目任意位置都能正确导入 src 模块
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # Moon_Dance 目录
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pymongo import MongoClient, DESCENDING, ASCENDING
from src.utils.mongo_db import MONGO_URI, DB_NAME

# ============================================================
# 健康评分算法参数（可按需调整）
# ============================================================
# 久坐时长维度 (满分 40 分)
MAX_DURATION_SCORE = 40
IDEAL_SEATED_MINUTES = 480       # 理想每日入座时长上限 (8小时)
OVER_SEATED_PENALTY_RATE = 0.05  # 每超出1分钟扣 0.05 分

# 坐姿质量维度 (满分 40 分)
MAX_POSTURE_SCORE = 40

# 坐姿稳定性维度 (满分 20 分)
MAX_CONSISTENCY_SCORE = 20
BAD_POSTURE_FREE_QUOTA = 5       # 允许5次以内不扣分
BAD_POSTURE_FULL_PENALTY = 50    # 超过50次稳定性得0分

# 不良坐姿判定阈值
BAD_POSTURE_RATIO_THRESHOLD = 0.10  # 偏差比率 > 10% 即判定为不良坐姿

# 数据采样间隔推算（秒） —— 两条数据间隔 ≤ 此值视为"连续入座"
SAMPLE_INTERVAL_SECONDS = 10


def get_db():
    """获取 MongoDB 数据库实例"""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')  # 验证连接
    return client[DB_NAME]


def calculate_health_score(total_seated_minutes, bad_posture_count,
                           good_posture_ratio):
    """
    计算健康评分 (0-100 分)

    三个维度：
    1. 久坐时长维度 (满分40)：入座越接近理想时长得分越高，过度久坐扣分
    2. 坐姿质量维度 (满分40)：良好坐姿占比越高得分越高
    3. 坐姿稳定性维度 (满分20)：不良坐姿次数越少得分越高

    :param total_seated_minutes: 当日总入座时长（分钟）
    :param bad_posture_count: 当日不良坐姿次数
    :param good_posture_ratio: 当日良好坐姿数据占比 (0~1)
    :return: (总分, 各维度明细字典)
    """
    # ---- 维度1: 久坐时长得分 ----
    if total_seated_minutes <= IDEAL_SEATED_MINUTES:
        # 入座时长合理，不扣分
        duration_score = MAX_DURATION_SCORE
    else:
        # 超时部分按比例扣分
        over_minutes = total_seated_minutes - IDEAL_SEATED_MINUTES
        penalty = over_minutes * OVER_SEATED_PENALTY_RATE
        duration_score = max(0, MAX_DURATION_SCORE - penalty)

    # ---- 维度2: 坐姿质量得分 ----
    # 良好坐姿占比直接乘以满分
    posture_score = good_posture_ratio * MAX_POSTURE_SCORE

    # ---- 维度3: 坐姿稳定性得分 ----
    if bad_posture_count <= BAD_POSTURE_FREE_QUOTA:
        consistency_score = MAX_CONSISTENCY_SCORE
    elif bad_posture_count >= BAD_POSTURE_FULL_PENALTY:
        consistency_score = 0
    else:
        # 在 [5, 50] 区间内线性递减
        ratio = (bad_posture_count - BAD_POSTURE_FREE_QUOTA) / \
                (BAD_POSTURE_FULL_PENALTY - BAD_POSTURE_FREE_QUOTA)
        consistency_score = MAX_CONSISTENCY_SCORE * (1 - ratio)

    # 所有维度取整组合
    duration_score = round(duration_score, 1)
    posture_score = round(posture_score, 1)
    consistency_score = round(consistency_score, 1)
    total = round(duration_score + posture_score + consistency_score)
    total = max(0, min(100, total))  # 限制在 [0, 100]

    breakdown = {
        "duration_score": duration_score,
        "posture_score": posture_score,
        "consistency_score": consistency_score
    }
    return total, breakdown


def aggregate_daily_data(db, target_date=None):
    """
    核心聚合逻辑：读取指定日期的原始数据，按设备分组汇总

    :param db: MongoDB 数据库实例
    :param target_date: 需要汇总的日期 (date 对象)，默认为昨天
    """
    if target_date is None:
        target_date = (datetime.now() - timedelta(days=1)).date()

    date_str = target_date.strftime("%Y-%m-%d")
    print(f"\n{'='*60}")
    print(f"  📊 开始汇总日期: {date_str}")
    print(f"{'='*60}")

    # ---- 计算当天的毫秒级时间戳范围 ----
    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = day_start + timedelta(days=1)
    start_ms = int(day_start.timestamp() * 1000)
    end_ms = int(day_end.timestamp() * 1000)

    raw_col = db["raw_device_data"]
    daily_col = db["daily_stats"]
    users_col = db["users"]

    # ---- 第一步：使用 MongoDB 聚合管道按设备分组统计 ----
    pipeline = [
        # 筛选时间范围内的数据
        {
            "$match": {
                "timestamp": {"$gte": start_ms, "$lt": end_ms}
            }
        },
        # 按设备 ID 分组
        {
            "$group": {
                "_id": "$device_id",
                "total_records": {"$sum": 1},                    # 总数据条数
                "bad_posture_count": {                           # 不良坐姿次数
                    "$sum": {
                        "$cond": [
                            {"$gt": [
                                {"$abs": {"$ifNull": [
                                    "$analysis.deviation_ratio", 0
                                ]}},
                                BAD_POSTURE_RATIO_THRESHOLD
                            ]},
                            1, 0
                        ]
                    }
                },
                "seated_records": {                              # 入座状态的记录数
                    "$sum": {
                        "$cond": [
                            {"$ifNull": ["$is_seated", True]},   # 默认视为入座
                            1, 0
                        ]
                    }
                },
                "timestamps": {"$push": "$timestamp"},           # 收集所有时间戳用于时长计算
                "hours": {                                       # 收集小时用于分布统计
                    "$push": {
                        "$toString": {
                            "$hour": {"$toDate": "$timestamp"}
                        }
                    }
                }
            }
        }
    ]

    results = list(raw_col.aggregate(pipeline))

    if not results:
        print(f"  ⚠️  {date_str} 没有找到任何原始数据，跳过汇总。")
        return 0

    print(f"  📡 找到 {len(results)} 个设备的数据，开始逐一计算...\n")

    count = 0
    for group in results:
        device_id = group["_id"]
        total_records = group["total_records"]
        bad_count = group["bad_posture_count"]
        seated_records = group["seated_records"]

        # ---- 计算总入座时长 ----
        # 按数据采样间隔推算：每条入座记录约代表 SAMPLE_INTERVAL_SECONDS 秒
        total_seated_minutes = round(
            (seated_records * SAMPLE_INTERVAL_SECONDS) / 60, 1
        )

        # ---- 计算良好坐姿比例 ----
        good_count = total_records - bad_count
        good_ratio = good_count / total_records if total_records > 0 else 1.0

        # ---- 计算健康评分 ----
        health_score, score_breakdown = calculate_health_score(
            total_seated_minutes, bad_count, good_ratio
        )

        # ---- 构建小时分布统计（用于热力图） ----
        hourly_dist = {}
        for h in group.get("hours", []):
            # 补齐为两位数
            h_padded = h.zfill(2)
            hourly_dist[h_padded] = hourly_dist.get(h_padded, 0) + 1

        # ---- 查找设备关联的用户 ----
        user = users_col.find_one({"device_id": device_id})
        user_id = user["_id"] if user else None

        # ---- 构造每日汇总文档 ----
        daily_doc = {
            "user_id": user_id,
            "device_id": device_id,
            "date": date_str,
            "total_seated_minutes": total_seated_minutes,
            "bad_posture_count": bad_count,
            "good_posture_ratio": round(good_ratio, 4),
            "health_score": health_score,
            "score_breakdown": score_breakdown,
            "hourly_distribution": hourly_dist,
            "total_raw_records": total_records,
            "created_at": datetime.utcnow()
        }

        # ---- 使用 upsert 写入，避免重复执行产生重复数据 ----
        filter_key = {"device_id": device_id, "date": date_str}
        daily_col.update_one(filter_key, {"$set": daily_doc}, upsert=True)

        # ---- 同步更新用户累计总积分 ----
        if user_id:
            users_col.update_one(
                {"_id": user_id},
                {"$inc": {"total_score": health_score}}
            )

        count += 1
        print(f"  ✅ [{device_id}] 入座 {total_seated_minutes} 分钟 | "
              f"不良姿势 {bad_count} 次 | "
              f"健康评分 {health_score} 分")

    print(f"\n  🎉 汇总完成！共处理 {count} 个设备的数据。")
    return count


def ensure_indexes(db):
    """确保必要的索引存在（首次运行时自动创建）"""
    print("  🔧 检查并创建索引...")

    # raw_device_data 索引
    raw_col = db["raw_device_data"]
    raw_col.create_index([("device_id", ASCENDING), ("timestamp", ASCENDING)],
                         name="idx_device_timestamp")

    # daily_stats 索引
    daily_col = db["daily_stats"]
    daily_col.create_index([("date", ASCENDING), ("health_score", DESCENDING)],
                           name="idx_date_score")
    daily_col.create_index([("user_id", ASCENDING), ("date", DESCENDING)],
                           name="idx_user_date")
    daily_col.create_index([("device_id", ASCENDING), ("date", ASCENDING)],
                           unique=True, name="idx_device_date_unique")

    # users 索引
    users_col = db["users"]
    users_col.create_index([("openid", ASCENDING)], unique=True,
                           name="idx_openid_unique", sparse=True)
    users_col.create_index([("device_id", ASCENDING)],
                           name="idx_device")

    print("  ✅ 索引创建/验证完成。")


def run_daily_job():
    """定时任务入口：汇总昨天的数据"""
    print(f"\n⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 定时任务触发")
    try:
        db = get_db()
        ensure_indexes(db)
        aggregate_daily_data(db)
    except Exception as e:
        print(f"  ❌ 定时任务执行失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description="每日数据汇总定时任务")
    parser.add_argument("--run-now", action="store_true",
                        help="立即执行一次汇总（默认汇总昨天的数据）")
    parser.add_argument("--date", type=str, default=None,
                        help="指定汇总日期，格式 YYYY-MM-DD（用于补跑历史数据）")
    parser.add_argument("--daemon", action="store_true",
                        help="以守护进程模式运行（APScheduler 定时执行）")
    args = parser.parse_args()

    if args.run_now or args.date:
        # ---- 手动执行模式 ----
        db = get_db()
        ensure_indexes(db)

        if args.date:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        else:
            target_date = None  # 默认昨天

        aggregate_daily_data(db, target_date)

    elif args.daemon:
        # ---- 守护进程模式：使用 APScheduler 定时执行 ----
        try:
            from apscheduler.schedulers.blocking import BlockingScheduler
        except ImportError:
            print("❌ 请先安装 APScheduler: pip install apscheduler")
            sys.exit(1)

        scheduler = BlockingScheduler()
        # 每天凌晨 00:05 执行（给前一天最后几秒数据入库的缓冲时间）
        scheduler.add_job(run_daily_job, 'cron', hour=0, minute=5,
                          id='daily_aggregation',
                          name='每日健康数据汇总',
                          replace_existing=True)

        print("=" * 60)
        print("  🚀 每日汇总定时任务已启动")
        print("  📅 执行时间: 每天 00:05")
        print("  💡 按 Ctrl+C 退出")
        print("=" * 60)

        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            print("\n  ⏹️ 定时任务已停止。")

    else:
        # 默认行为：立即执行一次
        print("💡 提示: 使用 --daemon 参数可以启动定时守护进程模式")
        print("         使用 --run-now 手动执行一次")
        print("         使用 --date YYYY-MM-DD 补跑指定日期\n")
        run_daily_job()


if __name__ == "__main__":
    main()
