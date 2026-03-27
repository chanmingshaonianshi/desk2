#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from datetime import datetime, timedelta, timezone
"""
文件：auth.py
实现了什么：定义了 API 接口的安全认证机制（Token 验证装饰器）。
怎么实现的：通过 functools.wraps 编写了 require_auth 装饰器，该装饰器会拦截所有 HTTP 请求，检查请求头（Authorization）中是否包含特定的 Bearer Token（默认为 moondance_secret_token_2024）。如果 Token 不存在或错误，直接返回 401 Unauthorized。
为什么实现：为了满足项目验收要求中的“加入 Token 身份验证机制，所有未授权的请求必须返回 403/401”。保护云端 API 不被恶意访问或遭受垃圾数据注入。
"""
from functools import wraps
from typing import Any, Callable, Dict, Tuple

import jwt
from flask import Blueprint, jsonify, request, g

from simulator.config.settings import API_APP_ID, API_APP_SECRET, JWT_ALGORITHM, JWT_EXPIRE_SECONDS, JWT_SECRET

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

