#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL 数据存储模块
功能：管理用户数据、设备绑定关系、久坐提醒设置、排行榜统计等关联关系数据
架构职责：MySQL 专门存储"人与数据的关联关系"，MongoDB 专门存储原始明细数据
使用原因：关系型数据（用户-设备绑定、排行榜排序、设置项）适合用 MySQL 管理，
         保证数据一致性和查询效率
"""

import os
import threading
import time
from datetime import datetime

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    DateTime, Text, UniqueConstraint, Index, inspect, text
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from src.config.settings import MYSQL_URI

# ============================================================
# SQLAlchemy 引擎与 Session 工厂
# ============================================================
engine = create_engine(
    MYSQL_URI,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    echo=False
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()
_init_lock = threading.Lock()
_init_done = False


def get_session() -> Session:
    """获取一个新的数据库 Session（使用完毕后需调用 .close()）"""
    ensure_initialized()
    return SessionLocal()


def ensure_initialized(max_retries: int = 10, retry_interval: float = 2.0) -> None:
    """确保 MySQL 可连接且数据表已创建。"""
    global _init_done
    if _init_done:
        return

    with _init_lock:
        if _init_done:
            return

        last_error = None
        for _ in range(max_retries):
            try:
                Base.metadata.create_all(bind=engine)
                _ensure_schema_updates()
                _init_done = True
                print("[MySQL] ✅ 数据库表初始化完成（users, user_daily_stats）")
                return
            except Exception as exc:
                last_error = exc
                time.sleep(retry_interval)

        print(f"[MySQL] ❌ 数据库表初始化失败: {last_error}")
        raise last_error


def _ensure_schema_updates() -> None:
    """对已存在的表补充新字段，兼容无迁移工具的线上环境。"""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("users")}
    if "password_hash" in columns:
        return

    with engine.begin() as conn:
        if engine.dialect.name == "mysql":
            conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NULL COMMENT '用户密码哈希'"))
        else:
            conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))


# ============================================================
# 数据模型定义
# ============================================================

class User(Base):
    """
    用户信息表
    存储：用户基本信息、openid、设备绑定关系、久坐提醒设置、隐私设置
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    openid = Column(String(128), unique=True, nullable=False, comment="微信 openid，唯一标识")
    nickname = Column(String(64), default="", comment="用户昵称")
    avatar_url = Column(String(512), default="", comment="头像 URL")
    device_id = Column(String(64), default="", index=True, comment="绑定的设备 ID")
    password_hash = Column(String(255), default="", comment="用户密码哈希")

    # 久坐提醒设置
    sedentary_threshold_min = Column(Integer, default=45, comment="久坐提醒阈值（分钟）")
    reminder_enabled = Column(Boolean, default=True, comment="是否开启久坐提醒")

    # 隐私设置
    visible_in_leaderboard = Column(Boolean, default=True, comment="是否在排行榜中可见")

    # 累计积分
    total_score = Column(Integer, default=0, comment="历史累计健康评分总和")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def to_dict(self):
        """将用户对象序列化为字典"""
        return {
            "id": self.id,
            "openid": self.openid,
            "nickname": self.nickname,
            "avatar_url": self.avatar_url,
            "device_id": self.device_id,
            "settings": {
                "sedentary_threshold_min": self.sedentary_threshold_min,
                "reminder_enabled": self.reminder_enabled,
                "visible_in_leaderboard": self.visible_in_leaderboard,
            },
            "total_score": self.total_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserDailyStat(Base):
    """
    用户每日统计表
    存储：每日健康评分、入座时长、不良坐姿次数等汇总数据
    用于排行榜查询和个人历史统计
    """
    __tablename__ = "user_daily_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True, comment="关联 users.id")
    device_id = Column(String(64), nullable=False, comment="设备 ID")
    date = Column(String(10), nullable=False, comment="统计日期 YYYY-MM-DD")

    # 核心统计指标
    total_seated_minutes = Column(Float, default=0, comment="总入座时长（分钟）")
    bad_posture_count = Column(Integer, default=0, comment="不良坐姿次数")
    good_posture_ratio = Column(Float, default=0, comment="良好坐姿占比 0~1")
    health_score = Column(Integer, default=0, comment="健康评分 0-100")

    # 评分明细
    duration_score = Column(Float, default=0, comment="久坐时长维度得分")
    posture_score = Column(Float, default=0, comment="坐姿质量维度得分")
    compliance_score = Column(Float, default=0, comment="久坐提醒合规维度得分")

    # 久坐提醒合规数据
    sedentary_reminders_total = Column(Integer, default=0, comment="当日久坐提醒总次数")
    sedentary_reminders_complied = Column(Integer, default=0, comment="用户合规离座次数（≥5分钟）")

    # 小时分布（JSON 字符串存储）
    hourly_distribution = Column(Text, default="{}", comment="每小时数据分布 JSON")

    # 原始记录数
    total_raw_records = Column(Integer, default=0, comment="当日原始数据条数")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 联合唯一约束：每个设备每天只有一条汇总
    __table_args__ = (
        UniqueConstraint("device_id", "date", name="uq_device_date"),
        Index("idx_date_score", "date", "health_score"),
        Index("idx_user_date", "user_id", "date"),
    )

    def to_dict(self):
        """将统计对象序列化为字典"""
        import json
        return {
            "id": self.id,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "date": self.date,
            "total_seated_minutes": self.total_seated_minutes,
            "bad_posture_count": self.bad_posture_count,
            "good_posture_ratio": self.good_posture_ratio,
            "health_score": self.health_score,
            "score_breakdown": {
                "duration_score": self.duration_score,
                "posture_score": self.posture_score,
                "compliance_score": self.compliance_score,
            },
            "sedentary_compliance": {
                "reminders_total": self.sedentary_reminders_total,
                "reminders_complied": self.sedentary_reminders_complied,
            },
            "hourly_distribution": json.loads(self.hourly_distribution or "{}"),
            "total_raw_records": self.total_raw_records,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================
# 数据库初始化
# ============================================================

def init_db():
    """
    初始化数据库：自动创建所有表（如果不存在）
    在服务启动时调用一次即可
    """
    ensure_initialized()


def check_connection():
    """检查 MySQL 连接是否正常"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "连接成功"
    except Exception as e:
        return False, str(e)

