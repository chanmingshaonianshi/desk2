#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL 数据库连接与功能验证脚本
功能：测试 MySQL 连接、自动建表、插入/查询用户数据和每日统计数据
"""

import os
import sys

# 路径处理
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from src.config.settings import MYSQL_URI


def main():
    print("=" * 60)
    print("  🔍 MySQL 数据库连接与功能验证")
    print("=" * 60)

    print(f"\n  📌 连接地址: {MYSQL_URI}")

    # ---- 第1步：测试连接 ----
    print("\n  [1/5] 测试数据库连接...")
    try:
        from src.utils.mysql_db import engine, check_connection, text
        ok, msg = check_connection()
        if ok:
            print(f"  ✅ 连接成功: {msg}")
        else:
            print(f"  ❌ 连接失败: {msg}")
            return
    except Exception as e:
        print(f"  ❌ 连接异常: {e}")
        return

    # ---- 第2步：自动建表 ----
    print("\n  [2/5] 初始化数据库表...")
    try:
        from src.utils.mysql_db import init_db
        init_db()
    except Exception as e:
        print(f"  ❌ 建表失败: {e}")
        return

    # ---- 第3步：插入测试用户 ----
    print("\n  [3/5] 插入测试用户...")
    try:
        from src.utils.mysql_db import get_session, User
        session = get_session()

        # 查找或创建
        test_user = session.query(User).filter(User.openid == "wx_test_mysql_001").first()
        if test_user:
            print(f"  📋 用户已存在: id={test_user.id}, nickname={test_user.nickname}")
        else:
            test_user = User(
                openid="wx_test_mysql_001",
                nickname="MySQL测试用户",
                avatar_url="",
                device_id="device_001",
                sedentary_threshold_min=45,
                reminder_enabled=True,
                visible_in_leaderboard=True,
                total_score=0,
            )
            session.add(test_user)
            session.commit()
            print(f"  ✅ 用户创建成功: id={test_user.id}, nickname={test_user.nickname}")

        session.close()
    except Exception as e:
        print(f"  ❌ 用户操作失败: {e}")
        return

    # ---- 第4步：插入测试统计数据 ----
    print("\n  [4/5] 插入测试每日统计...")
    try:
        from src.utils.mysql_db import get_session, UserDailyStat
        import json
        from datetime import datetime

        session = get_session()
        today_str = datetime.now().strftime("%Y-%m-%d")

        existing = session.query(UserDailyStat).filter(
            UserDailyStat.device_id == "device_001",
            UserDailyStat.date == today_str
        ).first()

        if existing:
            print(f"  📋 今日统计已存在: score={existing.health_score}")
        else:
            stat = UserDailyStat(
                user_id=test_user.id if test_user else None,
                device_id="device_001",
                date=today_str,
                total_seated_minutes=120.5,
                bad_posture_count=8,
                good_posture_ratio=0.85,
                health_score=88,
                posture_score=42.5,
                compliance_score=45.0,
                sedentary_reminders_total=3,
                sedentary_reminders_complied=2,
                hourly_distribution=json.dumps({"09": 50, "10": 40, "11": 30}),
                total_raw_records=500,
            )
            session.add(stat)
            session.commit()
            print(f"  ✅ 今日统计创建成功: score={stat.health_score}")

        session.close()
    except Exception as e:
        print(f"  ❌ 统计操作失败: {e}")
        return

    # ---- 第5步：查询验证 ----
    print("\n  [5/5] 查询验证数据...")
    try:
        from src.utils.mysql_db import get_session, User, UserDailyStat

        session = get_session()

        # 查询用户数
        user_count = session.query(User).count()
        print(f"  📊 users 表总记录数: {user_count}")

        # 查询统计数
        stat_count = session.query(UserDailyStat).count()
        print(f"  📊 user_daily_stats 表总记录数: {stat_count}")

        # 查询最新用户
        latest_user = session.query(User).order_by(User.id.desc()).first()
        if latest_user:
            print(f"  👤 最新用户: id={latest_user.id}, openid={latest_user.openid}, "
                  f"nickname={latest_user.nickname}, device={latest_user.device_id}")

        # 查询排行榜（按评分倒序）
        top_stats = session.query(UserDailyStat).order_by(
            UserDailyStat.health_score.desc()
        ).limit(5).all()

        if top_stats:
            print(f"\n  🏆 排行榜 TOP {len(top_stats)}:")
            for i, s in enumerate(top_stats, 1):
                print(f"    #{i} device={s.device_id} | date={s.date} | "
                      f"score={s.health_score} | seated={s.total_seated_minutes}min")

        session.close()
    except Exception as e:
        print(f"  ❌ 查询失败: {e}")
        return

    print(f"\n{'='*60}")
    print("  🎉 MySQL 全部验证通过！双数据库架构就绪。")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
