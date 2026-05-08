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

from src.config.settings import (
    API_APP_ID,
    API_APP_SECRET,
    API_KEY,
    JWT_ALGORITHM,
    JWT_EXPIRE_SECONDS,
    JWT_SECRET,
)

auth_bp = Blueprint("auth", __name__)


def _json_error(message: str, status_code: int) -> Tuple[Any, int]:
    return jsonify({"ok": False, "message": message}), status_code


def _issue_token(subject: str, *, token_type: str = "app", extra_claims: Dict[str, Any] | None = None,
                 expire_seconds: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    ttl = expire_seconds if expire_seconds is not None else JWT_EXPIRE_SECONDS
    exp = now + timedelta(seconds=ttl)
    payload: Dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def issue_miniapp_token(user_id: int, openid: str, expire_seconds: int | None = None) -> str:
    return _issue_token(
        str(user_id),
        token_type="miniapp_user",
        extra_claims={"uid": user_id, "openid": openid},
        expire_seconds=expire_seconds,
    )


def _decode_bearer_token() -> Dict[str, Any]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise ValueError("缺少 Authorization Bearer Token")

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise ValueError("Bearer Token 不能为空")

    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise ValueError("Token 已过期") from exc
    except Exception as exc:
        raise ValueError("Token 无效") from exc


def token_required(fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            payload = _decode_bearer_token()
        except ValueError:
            return _json_error("Forbidden", 403)

        if payload.get("type") not in {None, "app"}:
            return _json_error("Forbidden", 403)

        g.jwt_payload = payload
        return fn(*args, **kwargs)

    return wrapper


def api_key_required(fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        api_key = request.headers.get("X-API-Key", "").strip()
        if not api_key:
            return _json_error("缺少 X-API-Key", 401)
        if api_key != API_KEY:
            return _json_error("无效的 API Key", 401)
        return fn(*args, **kwargs)

    return wrapper


def miniapp_token_required(fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            payload = _decode_bearer_token()
        except ValueError as exc:
            return _json_error(str(exc), 401)

        if payload.get("type") != "miniapp_user":
            return _json_error("小程序用户 Token 无效", 401)

        g.miniapp_jwt_payload = payload
        return fn(*args, **kwargs)

    return wrapper


def miniapp_dual_auth_required(fn: Callable[..., Any]) -> Callable[..., Any]:
    @api_key_required
    @miniapp_token_required
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
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

    token = _issue_token(app_id, token_type="app")
    return jsonify({"ok": True, "token": token, "token_type": "Bearer", "expires_in": JWT_EXPIRE_SECONDS}), 200

