#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
身份鉴权模块
功能：JWT令牌签发、身份验证装饰器、登录接口实现
作用：保护API接口，只有合法客户端才能调用上传等接口
使用原因：统一鉴权逻辑，避免每个接口重复实现身份校验
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, Dict, Tuple

import jwt
from flask import Blueprint, jsonify, request, g

from src.config.settings import API_APP_ID, API_APP_SECRET, JWT_ALGORITHM, JWT_EXPIRE_SECONDS, JWT_SECRET

auth_bp = Blueprint("auth", __name__)


def _json_error(message: str, status_code: int) -> Tuple[Any, int]:
    return jsonify({"ok": False, "message": message}), status_code


def _issue_token(app_id: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=JWT_EXPIRE_SECONDS)
    payload: Dict[str, Any] = {
        "sub": app_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def token_required(fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return _json_error("Forbidden", 403)

        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            return _json_error("Forbidden", 403)

        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except Exception:
            return _json_error("Forbidden", 403)

        g.jwt_payload = payload
        return fn(*args, **kwargs)

    return wrapper


@auth_bp.post("/login")
def login() -> Tuple[Any, int]:
    data = request.get_json(silent=True) or {}
    app_id = str(data.get("app_id", "")).strip()
    app_secret = str(data.get("app_secret", "")).strip()

    if not app_id or not app_secret:
        return _json_error("缺少 app_id 或 app_secret", 400)

    if app_id != API_APP_ID or app_secret != API_APP_SECRET:
        return _json_error("Forbidden", 403)

    token = _issue_token(app_id)
    return jsonify({"ok": True, "token": token, "token_type": "Bearer", "expires_in": JWT_EXPIRE_SECONDS}), 200

