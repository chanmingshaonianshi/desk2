#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日数据汇总定时任务
功能：每天凌晨从 MongoDB pressure_data 中读取前一天的海量原始数据，
     按设备/用户聚合计算"总入座时长"、"不良坐姿次数"和"健康评分(0-100)"，
     将汇总结果写入 MySQL user_daily_stats 表（同时保留 MongoDB daily_stats 写入兼容）。
使用方式：
     方式1: 直接运行本文件，APScheduler 将在每天 00:05 自动执行
     方式2: 命令行传参 --run-now 立即手动执行一次（用于测试/补跑）

数据库职责划分：
     MongoDB → 原始明细数据（pressure_data）
     MySQL  → 用户关联数据、每日统计汇总（users, user_daily_stats）
"""

import os
import sys
import json
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
# 健康评分算法参数（新版：坐姿质量 50 分 + 久坐合规 50 分）
# ============================================================
# 不良坐姿判定阈值
BAD_POSTURE_RATIO_THRESHOLD = 0.10  # 偏差比率 > 10% 即判定为不良坐姿

# 数据采样间隔推算（秒） —— 两条数据间隔 ≤ 此值视为"连续入座"
SAMPLE_INTERVAL_SECONDS = 10

# 久坐提醒默认阈值（分钟），与 MySQL 用户表中的设置对应
DEFAULT_SEDENTARY_THRESHOLD_MIN = 45

# 离座合规判定：离座时长 ≥ 此值（秒）才视为"合规离座"
LEAVE_SEAT_COMPLIANCE_SECONDS = 300  # 5 分钟


def get_db():
    """获取 MongoDB 数据库实例"""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')  # 验证连接
    return client[DB_NAME]


def get_mysql_session():
    """获取 MySQL Session（懒加载导入，避免未安装时报错）"""
    try:
        from src.utils.mysql_db import get_session
        return get_session()
    except Exception as e:
        print(f"  [警告] MySQL 连接失败，将仅写入 MongoDB: {e}")
        return None


def get_user_sedentary_threshold(device_id):
    """从 MySQL 获取用户的久坐提醒阈值设置"""
    try:
        from src.utils.mysql_db import get_session, User
        session = get_session()
        user = session.query(User).filter(User.device_id == device_id).first()
        threshold = user.sedentary_threshold_min if user else DEFAULT_SEDENTARY_THRESHOLD_MIN
        session.close()
        return threshold
    except Exception:
        return DEFAULT_SEDENTARY_THRESHOLD_MIN


def analyze_sedentary_compliance(timestamps, sedentary_threshold_min):
    """
    分析久坐提醒合规情况

    逻辑：
    1. 将时间戳序列按时间排序
    2. 检测连续入座段（相邻数据间隔 ≤ SAMPLE_INTERVAL_SECONDS 秒）
    3. 当连续入座时长达到 sedentary_threshold_min 分钟时，记录一次"应提醒"
    4. 检查提醒后是否出现 ≥ 5 分钟的离座间隔（两条数据间隔 ≥ LEAVE_SEAT_COMPLIANCE_SECONDS）
    
    :param timestamps: 已排序的毫秒级时间戳列表
    :param sedentary_threshold_min: 久坐提醒阈值（分钟）
    :return: (总提醒次数, 合规离座次数)
    """
    if not timestamps or len(timestamps) < 2:
        return 0, 0

    threshold_ms = sedentary_threshold_min * 60 * 1000
    gap_threshold_ms = SAMPLE_INTERVAL_SECONDS * 1000

    reminders_total = 0
    reminders_complied = 0

    session_start = timestamps[0]
    last_ts = timestamps[0]
    pending_reminder = False  # 是否有一个待验证的提醒

    for i in range(1, len(timestamps)):
        current_ts = timestamps[i]
        gap = current_ts - last_ts

        if gap > gap_threshold_ms:
            # 出现间隔 → 离座
            if pending_reminder:
                # 检查离座时长是否 ≥ 5 分钟
                if gap >= LEAVE_SEAT_COMPLIANCE_SECONDS * 1000:
                    reminders_complied += 1
                pending_reminder = False

            # 开始新的入座段
            session_start = current_ts
        else:
            # 连续入座中，检查是否达到久坐阈值
            session_duration = current_ts - session_start
            if session_duration >= threshold_ms and not pending_reminder:
                reminders_total += 1
                pending_reminder = True
                # 重置入座起点，下一次达到阈值再触发
                session_start = current_ts

        last_ts = current_ts

    return reminders_total, reminders_complied


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
    print(f"  [汇总] 开始汇总日期: {date_str}")
    print(f"{'='*60}")

    # ---- 计算当天的毫秒级时间戳范围 ----
    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = day_start + timedelta(days=1)
    start_ms = int(day_start.timestamp() * 1000)
    end_ms = int(day_end.timestamp() * 1000)

    raw_col = db["pressure_data"]
    daily_col = db["daily_stats"]

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
        print(f"  [警告] {date_str} 没有找到任何原始数据，跳过汇总。")
        return 0

    print(f"  [数据] 找到 {len(results)} 个设备的数据，开始逐一计算...\n")

    # 获取 MySQL Session
    mysql_session = get_mysql_session()

    count = 0
    for group in results:
        device_id = group["_id"]
        total_records = group["total_records"]
        bad_count = group["bad_posture_count"]
        seated_records = group["seated_records"]

        # ---- 计算总入座时长 ----
        total_seated_minutes = round(
            (seated_records * SAMPLE_INTERVAL_SECONDS) / 60, 1
        )

        # ---- 计算良好坐姿比例 ----
        good_count = total_records - bad_count
        good_ratio = good_count / total_records if total_records > 0 else 1.0

        # ---- 分析久坐提醒合规情况 ----
        sorted_timestamps = sorted(group.get("timestamps", []))
        sedentary_threshold = get_user_sedentary_threshold(device_id)
        reminders_total, reminders_complied = analyze_sedentary_compliance(
            sorted_timestamps, sedentary_threshold
        )
        # 合规率：无提醒时默认 1.0（满分）
        compliance_ratio = (reminders_complied / reminders_total) if reminders_total > 0 else 1.0

        # ---- 计算新版健康评分 ----
        from src.core.posture_analyzer import calculate_health_score
        health_score, score_breakdown = calculate_health_score(
            good_ratio, compliance_ratio
        )

        # ---- 构建小时分布统计（用于热力图） ----
        hourly_dist = {}
        for h in group.get("hours", []):
            h_padded = h.zfill(2)
            hourly_dist[h_padded] = hourly_dist.get(h_padded, 0) + 1

        # ---- 写入 MongoDB daily_stats（兼容保留） ----
        daily_doc = {
            "device_id": device_id,
            "date": date_str,
            "total_seated_minutes": total_seated_minutes,
            "bad_posture_count": bad_count,
            "good_posture_ratio": round(good_ratio, 4),
            "health_score": health_score,
            "score_breakdown": score_breakdown,
            "sedentary_compliance": {
                "reminders_total": reminders_total,
                "reminders_complied": reminders_complied,
            },
            "hourly_distribution": hourly_dist,
            "total_raw_records": total_records,
            "created_at": datetime.utcnow()
        }

        filter_key = {"device_id": device_id, "date": date_str}
        daily_col.update_one(filter_key, {"$set": daily_doc}, upsert=True)

        # ---- 写入 MySQL user_daily_stats ----
        if mysql_session:
            try:
                from src.utils.mysql_db import UserDailyStat, User

                # 查找关联用户
                user = mysql_session.query(User).filter(
                    User.device_id == device_id
                ).first()
                user_id = user.id if user else None

                # upsert: 查找已有记录或创建新记录
                existing = mysql_session.query(UserDailyStat).filter(
                    UserDailyStat.device_id == device_id,
                    UserDailyStat.date == date_str
                ).first()

                if existing:
                    existing.user_id = user_id
                    existing.total_seated_minutes = total_seated_minutes
                    existing.bad_posture_count = bad_count
                    existing.good_posture_ratio = round(good_ratio, 4)
                    existing.health_score = health_score
                    existing.duration_score = 0  # 新算法不再使用此维度
                    existing.posture_score = score_breakdown["posture_score"]
                    existing.compliance_score = score_breakdown["compliance_score"]
                    existing.sedentary_reminders_total = reminders_total
                    existing.sedentary_reminders_complied = reminders_complied
                    existing.hourly_distribution = json.dumps(hourly_dist)
                    existing.total_raw_records = total_records
                else:
                    new_stat = UserDailyStat(
                        user_id=user_id,
                        device_id=device_id,
                        date=date_str,
                        total_seated_minutes=total_seated_minutes,
                        bad_posture_count=bad_count,
                        good_posture_ratio=round(good_ratio, 4),
                        health_score=health_score,
                        duration_score=0,
                        posture_score=score_breakdown["posture_score"],
                        compliance_score=score_breakdown["compliance_score"],
                        sedentary_reminders_total=reminders_total,
                        sedentary_reminders_complied=reminders_complied,
                        hourly_distribution=json.dumps(hourly_dist),
                        total_raw_records=total_records,
                    )
                    mysql_session.add(new_stat)

                # 更新用户累计总积分
                if user:
                    user.total_score = (user.total_score or 0) + health_score

                mysql_session.commit()
            except Exception as e:
                mysql_session.rollback()
                print(f"  [警告] [{device_id}] MySQL 写入失败: {e}")

        count += 1
        compliance_info = f"提醒{reminders_total}次/合规{reminders_complied}次"
        print(f"  [完成] [{device_id}] 入座 {total_seated_minutes} 分钟 | "
              f"不良姿势 {bad_count} 次 | "
              f"{compliance_info} | "
              f"健康评分 {health_score} 分")

    if mysql_session:
        mysql_session.close()

    print(f"\n  [完成] 汇总完成！共处理 {count} 个设备的数据。")
    return count


def ensure_indexes(db):
    """确保必要的索引存在（首次运行时自动创建）"""
    print("  [初始化] 检查并创建 MongoDB 索引...")

    # pressure_data 索引
    raw_col = db["pressure_data"]
    raw_col.create_index([("device_id", ASCENDING), ("timestamp", ASCENDING)],
                         name="idx_device_timestamp")

    # daily_stats 索引（兼容保留）
    daily_col = db["daily_stats"]
    daily_col.create_index([("date", ASCENDING), ("health_score", DESCENDING)],
                           name="idx_date_score")
    daily_col.create_index([("device_id", ASCENDING), ("date", ASCENDING)],
                           unique=True, name="idx_device_date_unique")

    print("  [完成] MongoDB 索引创建/验证完成。")

    # MySQL 表初始化
    try:
        from src.utils.mysql_db import init_db
        init_db()
    except Exception as e:
        print(f"  [警告] MySQL 表初始化失败（不影响 MongoDB 写入）: {e}")


def run_daily_job():
    """定时任务入口：汇总昨天的数据"""
    print(f"\n[定时任务] [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 定时任务触发")
    try:
        db = get_db()
        ensure_indexes(db)
        aggregate_daily_data(db)
    except Exception as e:
        print(f"  [错误] 定时任务执行失败: {e}")
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
            print("[错误] 请先安装 APScheduler: pip install apscheduler")
            sys.exit(1)

        scheduler = BlockingScheduler()
        # 每天凌晨 00:05 执行（给前一天最后几秒数据入库的缓冲时间）
        scheduler.add_job(run_daily_job, 'cron', hour=0, minute=5,
                          id='daily_aggregation',
                          name='每日健康数据汇总',
                          replace_existing=True)

        print("=" * 60)
        print("  [启动] 每日汇总定时任务已启动")
        print("  [时间] 执行时间: 每天 00:05")
        print("  [提示] 按 Ctrl+C 退出")
        print("=" * 60)

        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            print("\n  [停止] 定时任务已停止。")

    else:
        # 默认行为：立即执行一次
        print("[提示] 使用 --daemon 参数可以启动定时守护进程模式")
        print("         使用 --run-now 手动执行一次")
        print("         使用 --date YYYY-MM-DD 补跑指定日期\n")
        run_daily_job()


if __name__ == "__main__":
    main()
