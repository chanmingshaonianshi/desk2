#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小程序 API 路由模块
功能：为微信小程序提供实时状态查询、个人历史统计、排行榜等接口
作用：小程序端通过这些接口获取展示数据，完成 CRUD 操作
使用原因：与原有设备上报路由分离，保持清晰的模块职责划分
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from typing import Any, Tuple

from flask import Blueprint, jsonify, request
from pymongo import MongoClient, DESCENDING, ASCENDING
from bson import ObjectId

from src.utils.mongo_db import MONGO_URI, DB_NAME

# ============================================================
# Blueprint 定义
# ============================================================
miniapp_bp = Blueprint("miniapp", __name__, url_prefix="/api/miniapp")

# ============================================================
# 数据库连接（复用项目统一配置）
# ============================================================
_mongo_client = None


def _get_db():
    """获取 MongoDB 数据库实例（懒加载单例）"""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    return _mongo_client[DB_NAME]


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


# ============================================================
# API 1: 获取设备实时状态
# GET /api/miniapp/device/<device_id>/realtime
# ============================================================
@miniapp_bp.get("/device/<device_id>/realtime")
def get_device_realtime(device_id: str):
    """
    获取指定设备的实时状态

    从 raw_device_data 中读取该设备最近一条数据，
    并计算当前连续入座时长。

    返回数据：
    - 当前坐姿状态（正常/不良）
    - 左右压力值
    - 偏差比率
    - 当前连续入座时长（分钟）
    - 设备在线状态
    """
    try:
        db = _get_db()
        raw_col = db["raw_device_data"]

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
# API 2: 获取个人历史统计
# GET /api/miniapp/user/<user_id>/stats
# 支持查询参数: ?days=7 (默认7天) / ?start=2026-04-20&end=2026-04-27
# ============================================================
@miniapp_bp.get("/user/<user_id>/stats")
def get_user_stats(user_id: str):
    """
    获取指定用户的历史统计数据

    从 daily_stats 中查询该用户的每日汇总数据。
    支持按天数或日期范围查询。

    返回数据：
    - 每日统计列表（日期、入座时长、不良坐姿次数、健康评分）
    - 汇总信息（周期内平均评分、总入座时长等）
    """
    try:
        db = _get_db()
        daily_col = db["daily_stats"]
        users_col = db["users"]

        # ---- 尝试解析 user_id ----
        # 支持 ObjectId 和 openid 两种方式查找
        user = None
        try:
            user = users_col.find_one({"_id": ObjectId(user_id)})
        except Exception:
            pass
        if not user:
            user = users_col.find_one({"openid": user_id})

        # ---- 解析查询参数 ----
        days = request.args.get("days", type=int, default=7)
        start_date = request.args.get("start")
        end_date = request.args.get("end")

        if start_date and end_date:
            # 按日期范围查询
            query_filter = {"date": {"$gte": start_date, "$lte": end_date}}
        else:
            # 按最近N天查询
            today = datetime.now().date()
            start = today - timedelta(days=days - 1)
            query_filter = {
                "date": {
                    "$gte": start.strftime("%Y-%m-%d"),
                    "$lte": today.strftime("%Y-%m-%d")
                }
            }

        # ---- 添加用户过滤条件 ----
        if user:
            query_filter["user_id"] = user["_id"]
        else:
            # 如果没有找到用户记录，尝试用 user_id 作为 device_id 查询
            query_filter["device_id"] = user_id

        # ---- 执行查询 ----
        records = list(daily_col.find(
            query_filter,
            sort=[("date", ASCENDING)]
        ))

        # ---- 计算汇总信息 ----
        daily_list = []
        total_score = 0
        total_seated = 0
        total_bad = 0

        for r in records:
            doc = _serialize_doc(r)
            daily_list.append({
                "date": doc.get("date"),
                "total_seated_minutes": doc.get("total_seated_minutes", 0),
                "bad_posture_count": doc.get("bad_posture_count", 0),
                "good_posture_ratio": doc.get("good_posture_ratio", 0),
                "health_score": doc.get("health_score", 0),
                "score_breakdown": doc.get("score_breakdown", {}),
                "hourly_distribution": doc.get("hourly_distribution", {})
            })
            total_score += doc.get("health_score", 0)
            total_seated += doc.get("total_seated_minutes", 0)
            total_bad += doc.get("bad_posture_count", 0)

        num_days = len(daily_list)
        avg_score = round(total_score / num_days, 1) if num_days > 0 else 0

        result = {
            "user_id": str(user["_id"]) if user else user_id,
            "nickname": user.get("nickname", "未知用户") if user else "未知用户",
            "query_days": num_days,
            "summary": {
                "avg_health_score": avg_score,                # 平均健康评分
                "total_seated_minutes": round(total_seated, 1),  # 总入座时长
                "total_bad_posture_count": total_bad,         # 总不良坐姿次数
                "total_accumulated_score": user.get("total_score", 0) if user else 0
            },
            "daily_records": daily_list
        }

        return _json_ok(result)

    except Exception as e:
        return _json_error(f"查询历史统计失败: {str(e)}", 500)


# ============================================================
# API 3: 获取排行榜数据
# GET /api/miniapp/leaderboard
# 支持查询参数: ?date=2026-04-27 (默认今天) / ?limit=10
# ============================================================
@miniapp_bp.get("/leaderboard")
def get_leaderboard():
    """
    获取健康坐姿排行榜

    从 daily_stats 中按健康评分倒序排列，取出前 N 名。
    通过 user_id 关联 users 集合获取昵称等信息。

    返回数据：
    - 排行榜列表（排名、昵称、评分、入座时长、不良坐姿次数）
    """
    try:
        db = _get_db()
        daily_col = db["daily_stats"]
        users_col = db["users"]

        # ---- 解析查询参数 ----
        query_date = request.args.get("date")
        limit = request.args.get("limit", type=int, default=10)

        # 默认查询今天的排行榜；如果今天还没有数据，自动回退到昨天
        if not query_date:
            today_str = datetime.now().strftime("%Y-%m-%d")
            yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

            # 先尝试今天
            count = daily_col.count_documents({"date": today_str})
            query_date = today_str if count > 0 else yesterday_str

        # ---- 使用聚合管道进行排行榜查询 ----
        pipeline = [
            # 筛选指定日期的数据
            {"$match": {"date": query_date}},
            # 按健康评分倒序排列
            {"$sort": {"health_score": -1}},
            # 取前 N 名
            {"$limit": limit},
            # 关联 users 集合获取用户昵称和头像
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "user_info"
                }
            },
            # 展开用户信息（可能为空）
            {
                "$unwind": {
                    "path": "$user_info",
                    "preserveNullAndEmptyArrays": True
                }
            },
            # 投影需要返回的字段
            {
                "$project": {
                    "_id": 0,
                    "device_id": 1,
                    "health_score": 1,
                    "total_seated_minutes": 1,
                    "bad_posture_count": 1,
                    "good_posture_ratio": 1,
                    "score_breakdown": 1,
                    "nickname": {
                        "$ifNull": ["$user_info.nickname", "$device_id"]
                    },
                    "avatar_url": {
                        "$ifNull": ["$user_info.avatar_url", ""]
                    }
                }
            }
        ]

        rankings = list(daily_col.aggregate(pipeline))

        # ---- 构建排行榜响应 ----
        leaderboard = []
        for rank, entry in enumerate(rankings, 1):
            leaderboard.append({
                "rank": rank,                                  # 排名
                "nickname": entry.get("nickname", "匿名用户"),  # 昵称
                "avatar_url": entry.get("avatar_url", ""),     # 头像
                "device_id": entry.get("device_id", ""),       # 设备 ID
                "health_score": entry.get("health_score", 0),  # 健康评分
                "total_seated_minutes": entry.get("total_seated_minutes", 0),
                "bad_posture_count": entry.get("bad_posture_count", 0),
                "good_posture_ratio": entry.get("good_posture_ratio", 0),
                "score_breakdown": entry.get("score_breakdown", {})
            })

        result = {
            "date": query_date,
            "total_participants": daily_col.count_documents({"date": query_date}),
            "leaderboard": leaderboard
        }

        return _json_ok(result, f"{query_date} 排行榜数据")

    except Exception as e:
        return _json_error(f"查询排行榜失败: {str(e)}", 500)


# ============================================================
# API 4: 用户注册/更新（辅助接口）
# POST /api/miniapp/user/register
# ============================================================
@miniapp_bp.post("/user/register")
def register_user():
    """
    用户注册或更新信息

    小程序端在首次登录时调用，绑定 openid 和设备。
    如果用户已存在则更新信息。

    请求体：
    {
        "openid": "wx_user_xxx",
        "nickname": "用户昵称",
        "avatar_url": "https://...",
        "device_id": "device_001"
    }
    """
    try:
        db = _get_db()
        users_col = db["users"]

        data = request.get_json(silent=True) or {}
        openid = data.get("openid", "").strip()
        if not openid:
            return _json_error("缺少 openid 参数")

        # 构建用户文档
        user_doc = {
            "openid": openid,
            "nickname": data.get("nickname", f"用户_{openid[-6:]}"),
            "avatar_url": data.get("avatar_url", ""),
            "device_id": data.get("device_id", ""),
            "updated_at": datetime.utcnow()
        }

        # 使用 upsert：存在则更新，不存在则创建
        result = users_col.update_one(
            {"openid": openid},
            {
                "$set": user_doc,
                "$setOnInsert": {
                    "total_score": 0,
                    "settings": {
                        "sedentary_threshold_min": 45,
                        "reminder_enabled": True,
                        "visible_in_leaderboard": True
                    },
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )

        # 获取完整的用户文档返回给小程序
        user = users_col.find_one({"openid": openid})
        return _json_ok(_serialize_doc(user), "注册/更新成功")

    except Exception as e:
        return _json_error(f"用户注册失败: {str(e)}", 500)


# ============================================================
# API 5: 更新用户设置（辅助接口）
# PUT /api/miniapp/user/<user_id>/settings
# ============================================================
@miniapp_bp.put("/user/<user_id>/settings")
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
    try:
        db = _get_db()
        users_col = db["users"]

        data = request.get_json(silent=True) or {}

        # 构建需要更新的 settings 字段
        update_fields = {}
        if "sedentary_threshold_min" in data:
            threshold = int(data["sedentary_threshold_min"])
            threshold = max(10, min(120, threshold))  # 限制在10-120分钟
            update_fields["settings.sedentary_threshold_min"] = threshold
        if "reminder_enabled" in data:
            update_fields["settings.reminder_enabled"] = bool(data["reminder_enabled"])
        if "visible_in_leaderboard" in data:
            update_fields["settings.visible_in_leaderboard"] = bool(data["visible_in_leaderboard"])

        if not update_fields:
            return _json_error("没有提供需要更新的设置项")

        update_fields["updated_at"] = datetime.utcnow()

        # 尝试用 ObjectId 或 openid 查找用户
        query = None
        try:
            query = {"_id": ObjectId(user_id)}
        except Exception:
            query = {"openid": user_id}

        result = users_col.update_one(query, {"$set": update_fields})

        if result.matched_count == 0:
            return _json_error(f"未找到用户 {user_id}", 404)

        user = users_col.find_one(query)
        return _json_ok(_serialize_doc(user), "设置更新成功")

    except Exception as e:
        return _json_error(f"更新设置失败: {str(e)}", 500)
