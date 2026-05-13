#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小程序 API 路由模块
功能：为微信小程序提供实时状态查询、个人历史统计、排行榜等接口
作用：小程序端通过这些接口获取展示数据，完成 CRUD 操作
使用原因：与原有设备上报路由分离，保持清晰的模块职责划分

数据库职责划分：
    MongoDB → 实时传感器数据查询（pressure_data）
    MySQL  → 用户管理、排行榜、历史统计汇总（users, user_daily_stats）
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from typing import Any, Tuple

from flask import Blueprint, jsonify, request, g
from pymongo import MongoClient, DESCENDING, ASCENDING
from bson import ObjectId
from werkzeug.security import check_password_hash, generate_password_hash

from src.api.auth import api_key_required, issue_miniapp_token, miniapp_dual_auth_required
from src.utils.mongo_db import MONGO_URI, DB_NAME

# ============================================================
# Blueprint 定义
# ============================================================
miniapp_bp = Blueprint("miniapp", __name__, url_prefix="/api/miniapp")

# ============================================================
# MongoDB 连接（仅用于实时传感器数据查询）
# ============================================================
_mongo_client = None


def _get_mongo_db():
    """获取 MongoDB 数据库实例（懒加载单例）—— 仅用于 pressure_data 实时查询"""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    return _mongo_client[DB_NAME]


# ============================================================
# MySQL Session 工具
# ============================================================
def _get_mysql_session():
    """获取 MySQL 数据库 Session"""
    from src.utils.mysql_db import get_session
    return get_session()


def _json_ok(data: Any, message: str = "success") -> Tuple[Any, int]:
    """构造统一的成功响应"""
    return jsonify({"ok": True, "message": message, "data": data}), 200


def _json_error(message: str, status_code: int = 400) -> Tuple[Any, int]:
    """构造统一的错误响应"""
    return jsonify({"ok": False, "message": message, "data": None}), status_code


def _serialize_doc(doc: dict) -> dict:
    """将 MongoDB 文档中的 ObjectId 转为字符串，便于 JSON 序列化"""
    if doc is None:
        return {}
    result = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            result[k] = str(v)
        elif isinstance(v, datetime):
            result[k] = v.isoformat()
        elif isinstance(v, dict):
            result[k] = _serialize_doc(v)
        else:
            result[k] = v
    return result


def _parse_date_arg(value: str | None, field_name: str) -> str | None:
    """校验 YYYY-MM-DD 日期参数格式。"""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"{field_name} 参数格式错误，应为 YYYY-MM-DD") from exc


def _parse_bool_arg(value: Any, field_name: str) -> bool:
    """解析布尔参数，拒绝模糊值。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "1", "yes", "on"}:
            return True
        if text in {"false", "0", "no", "off"}:
            return False
    raise ValueError(f"{field_name} 参数必须为布尔值")


def _resolve_user(session, user_id: str):
    from src.utils.mysql_db import User

    user = None
    try:
        uid = int(user_id)
        user = session.query(User).filter(User.id == uid).first()
    except (ValueError, TypeError):
        pass
    if not user:
        user = session.query(User).filter(User.openid == user_id).first()
    return user


def _unbind_device_from_other_users(session, device_id: str, current_user_id: int | None) -> None:
    """确保同一个 device_id 只绑定到一个用户。"""
    from src.utils.mysql_db import User

    if not device_id:
        return

    query = session.query(User).filter(User.device_id == device_id)
    if current_user_id is not None:
        query = query.filter(User.id != current_user_id)

    for other_user in query.all():
        other_user.device_id = ""
        other_user.updated_at = datetime.utcnow()


def _ensure_user_access(requested_user_id: str):
    payload = getattr(g, "miniapp_jwt_payload", {})
    token_uid = str(payload.get("uid", "")).strip()
    token_openid = str(payload.get("openid", "")).strip()
    request_key = str(requested_user_id).strip()
    if request_key and request_key not in {token_uid, token_openid}:
        return _json_error("无权访问其他用户的数据", 403)
    return None


# ============================================================
# API 1: 获取设备实时状态（数据源：MongoDB）
# GET /api/miniapp/device/<device_id>/realtime
# ============================================================
@miniapp_bp.get("/device/<device_id>/realtime")
@miniapp_dual_auth_required
def get_device_realtime(device_id: str):
    """
    获取指定设备的实时状态

    从 MongoDB pressure_data 中读取该设备最近一条数据，
    并计算当前连续入座时长。

    返回数据：
    - 当前坐姿状态（正常/不良）
    - 左右压力值
    - 偏差比率
    - 当前连续入座时长（分钟）
    - 设备在线状态
    """
    try:
        db = _get_mongo_db()
        raw_col = db["pressure_data"]

        # ---- 获取该设备最近一条数据 ----
        latest = raw_col.find_one(
            {"device_id": device_id},
            sort=[("timestamp", DESCENDING)]
        )

        if not latest:
            return _json_error(f"未找到设备 {device_id} 的数据", 404)

        # ---- 判断设备是否在线 ----
        # 如果最后一条数据距今超过 60 秒，视为离线
        now_ms = int(time.time() * 1000)
        last_ts = latest.get("timestamp", 0)
        is_online = (now_ms - last_ts) < 60000  # 60 秒内有数据即在线

        # ---- 计算当前连续入座时长 ----
        # 从最近的数据向前回溯，找到连续入座的起点
        continuous_minutes = 0
        if is_online:
            # 查找最近 4 小时内的数据（避免扫描过多数据）
            four_hours_ago_ms = now_ms - (4 * 60 * 60 * 1000)
            recent_records = list(raw_col.find(
                {
                    "device_id": device_id,
                    "timestamp": {"$gte": four_hours_ago_ms}
                },
                sort=[("timestamp", DESCENDING)],
                limit=2000  # 最多回溯 2000 条
            ))

            if recent_records:
                # 从最新数据开始向前检查连续性
                # 如果相邻两条数据间隔 > 30秒，视为中断
                continuous_end = recent_records[0]["timestamp"]
                continuous_start = continuous_end
                for i in range(1, len(recent_records)):
                    gap = recent_records[i - 1]["timestamp"] - recent_records[i]["timestamp"]
                    if gap > 30000:  # 间隔超过30秒，入座中断
                        break
                    continuous_start = recent_records[i]["timestamp"]

                continuous_minutes = round(
                    (continuous_end - continuous_start) / 60000, 1
                )

        # ---- 提取传感器数据 ----
        sensors = latest.get("sensors", {})
        analysis = latest.get("analysis", {})
        deviation = analysis.get("deviation_ratio", 0)

        # 坐姿判定：偏差比率 > 10% 视为不良坐姿
        posture_status = "bad" if abs(deviation) > 0.10 else "normal"

        result = {
            "device_id": device_id,
            "is_online": is_online,
            "last_update_ms": last_ts,
            "posture_status": posture_status,           # 当前坐姿: "normal" | "bad"
            "posture_label": "标准坐姿 ✅" if posture_status == "normal" else "不良坐姿 ⚠️",
            "sensors": {
                "left_force_n": sensors.get("left_force_n", 0),
                "right_force_n": sensors.get("right_force_n", 0)
            },
            "deviation_ratio": round(deviation, 4),
            "continuous_seated_minutes": continuous_minutes,  # 当前连续入座时长
            "is_seated": latest.get("is_seated", True)
        }

        return _json_ok(result)

    except Exception as e:
        return _json_error(f"查询设备实时状态失败: {str(e)}", 500)


# ============================================================
# API 2: 获取个人历史统计（数据源：MySQL）
# GET /api/miniapp/user/<user_id>/stats
# 支持查询参数: ?days=7 (默认7天) / ?start=2026-04-20&end=2026-04-27
# ============================================================
@miniapp_bp.get("/user/me/stats")
@miniapp_dual_auth_required
def get_my_stats():
    """获取当前登录用户的历史统计数据（推荐：避免前端误用 user_id 导致 403）。"""
    payload = getattr(g, "miniapp_jwt_payload", {})
    uid = payload.get("uid")
    if not uid:
        return _json_error("Token 无效", 401)
    return get_user_stats(str(uid))


@miniapp_bp.get("/user/<user_id>/stats")
@miniapp_dual_auth_required
def get_user_stats(user_id: str):
    """
    获取指定用户的历史统计数据

    从 MySQL user_daily_stats 表中查询该用户的每日汇总数据。
    支持按天数或日期范围查询。

    返回数据：
    - 每日统计列表（日期、入座时长、不良坐姿次数、健康评分）
    - 汇总信息（周期内平均评分、总入座时长等）
    """
    session = None
    try:
        from src.utils.mysql_db import UserDailyStat

        session = _get_mysql_session()
        auth_error = _ensure_user_access(user_id)
        if auth_error:
            return auth_error

        # ---- 查找用户 ----
        user = _resolve_user(session, user_id)
        if not user:
            return _json_error(f"未找到用户 {user_id}", 404)

        # ---- 解析查询参数 ----
        days = request.args.get("days", type=int, default=7)
        if days <= 0 or days > 365:
            return _json_error("days 参数范围必须在 1-365 之间")

        start_date = _parse_date_arg(request.args.get("start"), "start")
        end_date = _parse_date_arg(request.args.get("end"), "end")

        if start_date and end_date:
            if start_date > end_date:
                return _json_error("start 不能晚于 end")
            date_start = start_date
            date_end = end_date
        else:
            today = datetime.now().date()
            start = today - timedelta(days=days - 1)
            date_start = start.strftime("%Y-%m-%d")
            date_end = today.strftime("%Y-%m-%d")

        # ---- 构建查询 ----
        query = session.query(UserDailyStat).filter(
            UserDailyStat.date >= date_start,
            UserDailyStat.date <= date_end
        )

        query = query.filter(UserDailyStat.user_id == user.id)

        records = query.order_by(UserDailyStat.date.asc()).all()

        # ---- 计算汇总信息 ----
        daily_list = []
        total_score = 0
        total_seated = 0
        total_bad = 0

        for r in records:
            doc = r.to_dict()
            daily_list.append({
                "date": doc.get("date"),
                "total_seated_minutes": doc.get("total_seated_minutes", 0),
                "bad_posture_count": doc.get("bad_posture_count", 0),
                "good_posture_ratio": doc.get("good_posture_ratio", 0),
                "health_score": doc.get("health_score", 0),
                "score_breakdown": doc.get("score_breakdown", {}),
                "sedentary_compliance": doc.get("sedentary_compliance", {}),
                "hourly_distribution": doc.get("hourly_distribution", {})
            })
            total_score += doc.get("health_score", 0)
            total_seated += doc.get("total_seated_minutes", 0)
            total_bad += doc.get("bad_posture_count", 0)

        num_days = len(daily_list)
        avg_score = round(total_score / num_days, 1) if num_days > 0 else 0

        result = {
            "user_id": str(user.id),
            "nickname": user.nickname,
            "query_days": num_days,
            "summary": {
                "avg_health_score": avg_score,                # 平均健康评分
                "total_seated_minutes": round(total_seated, 1),  # 总入座时长
                "total_bad_posture_count": total_bad,         # 总不良坐姿次数
                "total_accumulated_score": user.total_score
            },
            "daily_records": daily_list
        }

        return _json_ok(result)

    except Exception as e:
        return _json_error(f"查询历史统计失败: {str(e)}", 500)
    finally:
        if session:
            session.close()


# ============================================================
# API 3: 获取排行榜数据（数据源：MySQL）
# GET /api/miniapp/leaderboard
# 支持查询参数: ?date=2026-04-27 (默认今天) / ?limit=10
# ============================================================
@miniapp_bp.get("/leaderboard")
@miniapp_dual_auth_required
def get_leaderboard():
    """
    获取健康坐姿排行榜

    从 MySQL user_daily_stats 中按健康评分倒序排列，取出前 N 名。
    通过 user_id 关联 users 表获取昵称等信息。

    返回数据：
    - 排行榜列表（排名、昵称、评分、入座时长、不良坐姿次数）
    """
    session = None
    try:
        from src.utils.mysql_db import User, UserDailyStat
        from sqlalchemy import func

        session = _get_mysql_session()

        # ---- 解析查询参数 ----
        query_date = _parse_date_arg(request.args.get("date"), "date")
        limit = request.args.get("limit", type=int, default=10)
        if limit <= 0 or limit > 100:
            return _json_error("limit 参数范围必须在 1-100 之间")

        # 默认查询今天的排行榜；如果今天还没有数据，自动回退到昨天
        if not query_date:
            today_str = datetime.now().strftime("%Y-%m-%d")
            yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

            count = session.query(func.count(UserDailyStat.id)).filter(
                UserDailyStat.date == today_str
            ).scalar()
            query_date = today_str if count > 0 else yesterday_str

        # ---- 查询排行榜数据（LEFT JOIN users 表） ----
        from sqlalchemy import outerjoin

        results = session.query(
            UserDailyStat, User
        ).outerjoin(
            User, UserDailyStat.user_id == User.id
        ).filter(
            UserDailyStat.date == query_date
        ).order_by(
            UserDailyStat.health_score.desc()
        ).limit(limit).all()

        # ---- 构建排行榜响应 ----
        leaderboard = []
        for rank, (stat, user) in enumerate(results, 1):
            leaderboard.append({
                "rank": rank,
                "nickname": user.nickname if user else stat.device_id,
                "avatar_url": user.avatar_url if user else "",
                "device_id": stat.device_id,
                "health_score": stat.health_score,
                "total_seated_minutes": stat.total_seated_minutes,
                "bad_posture_count": stat.bad_posture_count,
                "good_posture_ratio": stat.good_posture_ratio,
                "score_breakdown": {
                    "posture_score": stat.posture_score,
                    "compliance_score": stat.compliance_score,
                }
            })

        total_participants = session.query(func.count(UserDailyStat.id)).filter(
            UserDailyStat.date == query_date
        ).scalar()

        result = {
            "date": query_date,
            "total_participants": total_participants,
            "leaderboard": leaderboard
        }

        return _json_ok(result, f"{query_date} 排行榜数据")

    except Exception as e:
        return _json_error(f"查询排行榜失败: {str(e)}", 500)
    finally:
        if session:
            session.close()


# ============================================================
# API 4: 用户注册/更新（数据源：MySQL）
# POST /api/miniapp/user/register
# ============================================================
@miniapp_bp.post("/user/register")
@api_key_required
def register_user():
    """
    用户注册或更新信息

    小程序端在首次登录时调用，绑定 openid 和设备。
    如果用户已存在则更新信息。

    请求体：
    {
        "openid": "wx_user_xxx",
        "password": "plain_password",
        "nickname": "用户昵称",
        "avatar_url": "https://...",
        "device_id": "device_001"
    }
    """
    session = None
    try:
        from src.utils.mysql_db import User

        session = _get_mysql_session()

        data = request.get_json(silent=True) or {}
        openid = data.get("openid", "").strip()
        password = str(data.get("password", "")).strip()
        device_id = str(data.get("device_id", "")).strip()
        if not openid:
            return _json_error("缺少 openid 参数，不要直接传微信 login code")

        # 查找是否已存在
        user = session.query(User).filter(User.openid == openid).first()

        if user:
            # 更新已有用户
            user.nickname = data.get("nickname", user.nickname)
            user.avatar_url = data.get("avatar_url", user.avatar_url)
            if device_id:
                _unbind_device_from_other_users(session, device_id, user.id)
                user.device_id = device_id
            if password:
                user.password_hash = generate_password_hash(password)
            elif not (user.password_hash or "").strip():
                return _json_error("用户尚未设置密码，请补充 password 字段")
            user.updated_at = datetime.utcnow()
        else:
            if not password:
                return _json_error("首次注册必须提供 password")
            _unbind_device_from_other_users(session, device_id, None)
            # 创建新用户
            user = User(
                openid=openid,
                nickname=data.get("nickname", f"用户_{openid[-6:]}"),
                avatar_url=data.get("avatar_url", ""),
                device_id=device_id,
                password_hash=generate_password_hash(password),
                sedentary_threshold_min=45,
                reminder_enabled=True,
                visible_in_leaderboard=True,
                total_score=0,
            )
            session.add(user)

        session.commit()

        # 返回完整用户信息
        user_dict = user.to_dict()
        return _json_ok(user_dict, "注册/更新成功")

    except Exception as e:
        return _json_error(f"用户注册失败: {str(e)}", 500)
    finally:
        if session:
            session.close()


@miniapp_bp.post("/user/login")
@api_key_required
def login_miniapp_user():
    """小程序用户登录，返回 Bearer Token。"""
    session = None
    try:
        from src.utils.mysql_db import User

        session = _get_mysql_session()
        data = request.get_json(silent=True) or {}
        openid = str(data.get("openid", "")).strip()
        password = str(data.get("password", "")).strip()

        if not openid or not password:
            return _json_error("缺少 openid 或 password 参数")

        user = session.query(User).filter(User.openid == openid).first()
        if not user:
            return _json_error("用户不存在", 404)
        if not (user.password_hash or "").strip():
            return _json_error("用户尚未设置密码，请先注册并设置 password", 400)
        if not check_password_hash(user.password_hash, password):
            return _json_error("密码错误", 401)

        token = issue_miniapp_token(user.id, user.openid)
        result = {
            "token": token,
            "token_type": "Bearer",
            "user": user.to_dict(),
        }
        return _json_ok(result, "登录成功")
    except Exception as e:
        return _json_error(f"用户登录失败: {str(e)}", 500)
    finally:
        if session:
            session.close()


# ============================================================
# API 5: 更新用户设置（数据源：MySQL）
# PUT /api/miniapp/user/<user_id>/settings
# ============================================================
@miniapp_bp.put("/user/<user_id>/settings")
@miniapp_dual_auth_required
def update_user_settings(user_id: str):
    """
    更新用户设置（久坐提醒阈值等）

    请求体：
    {
        "sedentary_threshold_min": 30,
        "reminder_enabled": true,
        "visible_in_leaderboard": false
    }
    """
    session = None
    try:
        from src.utils.mysql_db import User

        session = _get_mysql_session()
        auth_error = _ensure_user_access(user_id)
        if auth_error:
            return auth_error

        data = request.get_json(silent=True) or {}

        # ---- 查找用户 ----
        user = _resolve_user(session, user_id)

        if not user:
            return _json_error(f"未找到用户 {user_id}", 404)

        # ---- 更新设置项 ----
        updated = False
        if "sedentary_threshold_min" in data:
            threshold = int(data["sedentary_threshold_min"])
            if threshold < 10 or threshold > 120:
                return _json_error("sedentary_threshold_min 必须在 10-120 分钟之间")
            user.sedentary_threshold_min = threshold
            updated = True
        if "reminder_enabled" in data:
            user.reminder_enabled = _parse_bool_arg(data["reminder_enabled"], "reminder_enabled")
            updated = True
        if "visible_in_leaderboard" in data:
            user.visible_in_leaderboard = _parse_bool_arg(data["visible_in_leaderboard"], "visible_in_leaderboard")
            updated = True

        if not updated:
            return _json_error("没有提供需要更新的设置项")

        user.updated_at = datetime.utcnow()
        session.commit()

        user_dict = user.to_dict()
        return _json_ok(user_dict, "设置更新成功")

    except Exception as e:
        return _json_error(f"更新设置失败: {str(e)}", 500)
    finally:
        if session:
            session.close()
