#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import hashlib
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, Dict, Tuple

import jwt
from flask import Blueprint, jsonify, request, g

try:
    from pymongo import MongoClient, DESCENDING
except ImportError:
    MongoClient = None
    DESCENDING = -1

from src.config.settings import API_KEY, JWT_ALGORITHM, JWT_SECRET
from src.utils.mongo_db import DB_NAME, MONGO_URI

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123456")
ADMIN_TOKEN_EXPIRE_SECONDS = int(os.environ.get("ADMIN_TOKEN_EXPIRE_SECONDS", "7200"))
ADMIN_DEVICE_LIMIT = int(os.environ.get("ADMIN_DEVICE_LIMIT", "1500"))

REGION_POOL = ["北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "武汉", "西安", "重庆"]
_mongo_client = None


def _json_ok(data: Any, message: str = "success") -> Tuple[Any, int]:
    return jsonify({"ok": True, "message": message, "data": data}), 200


def _json_error(message: str, status_code: int = 400) -> Tuple[Any, int]:
    return jsonify({"ok": False, "message": message, "data": None}), status_code


def _get_mongo_db():
    if MongoClient is None:
        raise RuntimeError("pymongo is not installed")
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2500)
    return _mongo_client[DB_NAME]


def _get_mysql_session():
    from src.utils.mysql_db import get_session
    return get_session()


def _issue_admin_token(username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "type": "admin",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ADMIN_TOKEN_EXPIRE_SECONDS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_admin_token() -> Dict[str, Any]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise ValueError("缺少管理员 Token")
    payload = jwt.decode(auth_header.split(" ", 1)[1].strip(), JWT_SECRET, algorithms=[JWT_ALGORITHM])
    if payload.get("type") != "admin":
        raise ValueError("管理员 Token 无效")
    return payload


def admin_required(fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if request.headers.get("X-API-Key", "").strip() != API_KEY:
            return _json_error("无效的 X-API-Key", 401)
        try:
            g.admin_jwt_payload = _decode_admin_token()
        except jwt.ExpiredSignatureError:
            return _json_error("管理员 Token 已过期", 401)
        except Exception as exc:
            return _json_error(str(exc), 401)
        return fn(*args, **kwargs)

    return wrapper


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _device_region(device_id: str) -> str:
    digest = hashlib.sha1(device_id.encode("utf-8")).hexdigest()
    return REGION_POOL[int(digest[:2], 16) % len(REGION_POOL)]


def _extract_device_id(record: Dict[str, Any]) -> str:
    value = record.get("device_id") or record.get("device") or ""
    if isinstance(value, int):
        return f"device_{value:03d}"
    text = str(value).strip()
    if text.isdigit():
        return f"device_{int(text):03d}"
    return text


def _extract_timestamp(record: Dict[str, Any]) -> int:
    return _safe_int(record.get("timestamp") or record.get("timestamp_ms") or record.get("logged_at"))


def _extract_sensor_values(record: Dict[str, Any]) -> Tuple[float, float, float, bool]:
    sensors = record.get("sensors") or {}
    analysis = record.get("analysis") or {}
    left = _safe_float(sensors.get("left_force_n", record.get("left_force_n", record.get("f_left", 0))))
    right = _safe_float(sensors.get("right_force_n", record.get("right_force_n", record.get("f_right", 0))))
    deviation = _safe_float(analysis.get("deviation_ratio", record.get("deviation_ratio", record.get("ratio", 0))))
    is_seated = bool(record.get("is_seated", left + right > 20))
    return left, right, deviation, is_seated


def _latest_records_by_device(limit: int | None = None) -> Dict[str, Dict[str, Any]]:
    latest: Dict[str, Dict[str, Any]] = {}
    device_limit = max(1, min(_safe_int(limit if limit is not None else ADMIN_DEVICE_LIMIT, ADMIN_DEVICE_LIMIT), 5000))
    scan_limit = device_limit * 20
    try:
        cursor = _get_mongo_db()["pressure_data"].find({}, {"_id": 0}).sort("timestamp", DESCENDING).limit(scan_limit)
        for record in cursor:
            device_id = _extract_device_id(record)
            if device_id and device_id not in latest:
                latest[device_id] = record
                if len(latest) >= device_limit:
                    break
    except Exception:
        return latest
    return latest


def _registered_users():
    session = None
    try:
        from src.utils.mysql_db import User

        session = _get_mysql_session()
        return session.query(User).order_by(User.updated_at.desc()).limit(1000).all()
    except Exception:
        return []
    finally:
        if session is not None:
            session.close()


def _stats_records(days: int):
    session = None
    try:
        from src.utils.mysql_db import UserDailyStat

        start_date = (datetime.now().date() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
        session = _get_mysql_session()
        return (
            session.query(UserDailyStat)
            .filter(UserDailyStat.date >= start_date)
            .order_by(UserDailyStat.date.asc())
            .limit(5000)
            .all()
        )
    except Exception:
        return []
    finally:
        if session is not None:
            session.close()


def _raw_records_since(days: int, limit: int = 6000):
    start_ms = int((time.time() - days * 86400) * 1000)
    try:
        return list(
            _get_mongo_db()["pressure_data"]
            .find({"timestamp": {"$gte": start_ms}}, {"_id": 0})
            .sort("timestamp", 1)
            .limit(limit)
        )
    except Exception:
        return []


@admin_bp.post("/login")
def login_admin():
    if request.headers.get("X-API-Key", "").strip() != API_KEY:
        return _json_error("无效的 X-API-Key", 401)

    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
        return _json_error("管理员账号或密码错误", 403)

    return _json_ok(
        {
            "token": _issue_admin_token(username),
            "token_type": "Bearer",
            "expires_in": ADMIN_TOKEN_EXPIRE_SECONDS,
            "admin": {"username": username},
        },
        "登录成功",
    )


@admin_bp.get("/summary")
@admin_required
def get_summary():
    latest = _latest_records_by_device()
    users = _registered_users()
    now_ms = int(time.time() * 1000)
    device_ids = set(latest.keys())
    device_ids.update(str(getattr(user, "device_id", "") or "").strip() for user in users if getattr(user, "device_id", ""))

    online = seated = bad_posture = 0
    deviations = []
    for device_id in device_ids:
        record = latest.get(device_id) or {}
        timestamp = _extract_timestamp(record)
        left, right, deviation, is_seated = _extract_sensor_values(record)
        online += int(bool(timestamp and now_ms - timestamp < 60000))
        seated += int(is_seated)
        bad_posture += int(abs(deviation) > 0.10)
        if left or right or deviation:
            deviations.append(abs(deviation))

    stats = _stats_records(30)
    return _json_ok(
        {
            "registered_devices": len([x for x in device_ids if x]),
            "online_devices": online,
            "seated_devices": seated,
            "bad_posture_devices": bad_posture,
            "registered_users": len(users),
            "avg_deviation_ratio": round(sum(deviations) / len(deviations), 4) if deviations else 0,
            "avg_health_score": round(sum(s.health_score for s in stats) / len(stats), 1) if stats else 0,
            "total_seated_minutes_30d": round(sum(s.total_seated_minutes for s in stats), 1) if stats else 0,
        }
    )


@admin_bp.get("/devices")
@admin_required
def get_devices():
    latest = _latest_records_by_device()
    users = _registered_users()
    now_ms = int(time.time() * 1000)
    user_by_device = {str(getattr(user, "device_id", "") or "").strip(): user for user in users if getattr(user, "device_id", "")}
    device_ids = sorted(set(latest.keys()) | set(user_by_device.keys()))[:ADMIN_DEVICE_LIMIT]

    devices = []
    for device_id in device_ids:
        record = latest.get(device_id) or {}
        left, right, deviation, is_seated = _extract_sensor_values(record)
        timestamp = _extract_timestamp(record)
        user = user_by_device.get(device_id)
        devices.append(
            {
                "device_id": device_id,
                "region": _device_region(device_id),
                "is_online": bool(timestamp and now_ms - timestamp < 60000),
                "last_update_ms": timestamp,
                "is_seated": is_seated,
                "posture_status": "bad" if abs(deviation) > 0.10 else "normal",
                "left_force_n": round(left, 1),
                "right_force_n": round(right, 1),
                "deviation_ratio": round(deviation, 4),
                "user_id": getattr(user, "id", None) if user else None,
                "nickname": getattr(user, "nickname", "") if user else "",
            }
        )

    return _json_ok({"total": len(devices), "devices": devices})


@admin_bp.get("/regions")
@admin_required
def get_regions():
    latest = _latest_records_by_device()
    users = _registered_users()
    device_ids = set(latest.keys())
    device_ids.update(str(getattr(user, "device_id", "") or "").strip() for user in users if getattr(user, "device_id", ""))
    counts = Counter(_device_region(device_id) for device_id in device_ids if device_id)
    return _json_ok({"regions": [{"name": name, "value": value} for name, value in counts.most_common()]})


@admin_bp.get("/analytics")
@admin_required
def get_analytics():
    days = max(1, min(_safe_int(request.args.get("days"), 30), 365))
    by_date = defaultdict(lambda: {
        "health_score_total": 0.0,
        "health_score_count": 0,
        "seated_minutes": 0.0,
        "bad_posture_count": 0,
        "good_posture_ratio_total": 0.0,
        "good_posture_ratio_count": 0,
    })

    for stat in _stats_records(days):
        item = by_date[stat.date]
        item["health_score_total"] += stat.health_score
        item["health_score_count"] += 1
        item["seated_minutes"] += stat.total_seated_minutes
        item["bad_posture_count"] += stat.bad_posture_count
        item["good_posture_ratio_total"] += stat.good_posture_ratio
        item["good_posture_ratio_count"] += 1

    raw_records = _raw_records_since(days)
    step = max(1, len(raw_records) // 300 or 1)
    pressure_points = []
    for record in raw_records[::step]:
        left, right, deviation, _ = _extract_sensor_values(record)
        ts = _extract_timestamp(record)
        if ts:
            pressure_points.append({
                "time": datetime.fromtimestamp(ts / 1000).strftime("%m-%d %H:%M"),
                "left_force_n": round(left, 1),
                "right_force_n": round(right, 1),
                "deviation_ratio": round(deviation, 4),
            })

    timeline = []
    for offset in range(days - 1, -1, -1):
        date_text = (datetime.now().date() - timedelta(days=offset)).strftime("%Y-%m-%d")
        item = by_date[date_text]
        timeline.append({
            "date": date_text,
            "avg_health_score": round(item["health_score_total"] / item["health_score_count"], 1)
            if item["health_score_count"] else 0,
            "total_seated_minutes": round(item["seated_minutes"], 1),
            "bad_posture_count": int(item["bad_posture_count"]),
            "good_posture_ratio": round(item["good_posture_ratio_total"] / item["good_posture_ratio_count"], 4)
            if item["good_posture_ratio_count"] else 0,
        })

    return _json_ok({"days": days, "timeline": timeline, "pressure_points": pressure_points})


@admin_bp.get("/users")
@admin_required
def get_users():
    users = []
    for user in _registered_users():
        users.append({
            "id": user.id,
            "openid": user.openid,
            "nickname": user.nickname,
            "device_id": user.device_id,
            "total_score": user.total_score,
            "sedentary_threshold_min": user.sedentary_threshold_min,
            "reminder_enabled": bool(user.reminder_enabled),
            "visible_in_leaderboard": bool(user.visible_in_leaderboard),
            "updated_at": user.updated_at.isoformat() if user.updated_at else "",
        })
    return _json_ok({"total": len(users), "users": users})
