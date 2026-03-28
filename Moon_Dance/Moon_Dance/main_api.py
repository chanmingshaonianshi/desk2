#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTPS API服务主入口模块
功能：启动Flask API服务、HTTPS证书管理、路由注册
作用：对外提供服务接口，支持多设备数据上传、身份鉴权
使用原因：独立于桌面端的服务入口，支持容器化部署和集群扩展
"""

from __future__ import annotations

import argparse
import os
import time
from typing import Tuple

from flask import Flask, jsonify
from flask_cors import CORS
from OpenSSL import crypto

import json
import time
from src.api.auth import auth_bp
from src.api.routes import api_bp
from src.config.settings import BASE_PATH, CA_CERT_FILE, CA_KEY_FILE, CERT_DIR, CERT_FILE, KEY_FILE, LOG_DIR


def _is_ip(value: str) -> bool:
    parts = value.split(".")
    if len(parts) != 4:
        return False
    for p in parts:
        if not p.isdigit():
            return False
        n = int(p)
        if n < 0 or n > 255:
            return False
    return True


def _ensure_ca_and_server_cert(cert_dir: str, common_name: str) -> Tuple[str, str, str]:
    os.makedirs(cert_dir, exist_ok=True)

    cert_path = os.path.join(cert_dir, CERT_FILE)
    key_path = os.path.join(cert_dir, KEY_FILE)
    ca_cert_path = os.path.join(cert_dir, CA_CERT_FILE)
    ca_key_path = os.path.join(cert_dir, CA_KEY_FILE)

    if os.path.exists(cert_path) and os.path.exists(key_path) and os.path.exists(ca_cert_path):
        return cert_path, key_path, ca_cert_path

    ca_key = crypto.PKey()
    ca_key.generate_key(crypto.TYPE_RSA, 2048)

    ca_cert = crypto.X509()
    ca_cert.get_subject().CN = "MoonDance Local CA"
    ca_cert.set_serial_number(int(time.time()))
    ca_cert.gmtime_adj_notBefore(0)
    ca_cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)
    ca_cert.set_issuer(ca_cert.get_subject())
    ca_cert.set_pubkey(ca_key)
    ca_cert.add_extensions(
        [
            crypto.X509Extension(b"basicConstraints", True, b"CA:TRUE, pathlen:0"),
            crypto.X509Extension(b"keyUsage", True, b"keyCertSign, cRLSign"),
            crypto.X509Extension(b"subjectKeyIdentifier", False, b"hash", subject=ca_cert),
        ]
    )
    ca_cert.sign(ca_key, "sha256")

    server_key = crypto.PKey()
    server_key.generate_key(crypto.TYPE_RSA, 2048)

    server_cert = crypto.X509()
    server_cert.get_subject().CN = common_name
    server_cert.set_serial_number(int(time.time()) + 1)
    server_cert.gmtime_adj_notBefore(0)
    server_cert.gmtime_adj_notAfter(3 * 365 * 24 * 60 * 60)
    server_cert.set_issuer(ca_cert.get_subject())
    server_cert.set_pubkey(server_key)

    san_items = []
    if common_name:
        if _is_ip(common_name):
            san_items.append(f"IP:{common_name}")
        else:
            san_items.append(f"DNS:{common_name}")
    san_items.extend(["DNS:localhost", "IP:127.0.0.1"])
    san_value = ", ".join(sorted(set(san_items)))

    server_cert.add_extensions(
        [
            crypto.X509Extension(b"basicConstraints", True, b"CA:FALSE"),
            crypto.X509Extension(b"keyUsage", True, b"digitalSignature, keyEncipherment"),
            crypto.X509Extension(b"extendedKeyUsage", False, b"serverAuth"),
            crypto.X509Extension(b"subjectAltName", False, san_value.encode("utf-8")),
        ]
    )
    server_cert.sign(ca_key, "sha256")

    with open(ca_cert_path, "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, ca_cert))
    with open(ca_key_path, "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, ca_key))
    with open(cert_path, "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, server_cert))
    with open(key_path, "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, server_key))

    return cert_path, key_path, ca_cert_path


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    # 请求日志中间件：每个接口请求数据单独写入文件
    @app.before_request
    def log_request_data():
        # 跳过静态资源等非API请求
        if request.path.startswith('/static'):
            return
            
        # 构造日志数据
        log_data = {
            "timestamp": int(time.time() * 1000),
            "method": request.method,
            "path": request.path,
            "remote_addr": request.remote_addr,
            "headers": dict(request.headers),
            "query_params": dict(request.args),
            "body": request.get_json(silent=True) or request.data.decode('utf-8', errors='ignore')
        }
        
        # 按接口路径命名文件，每个接口单独一个日志文件
        log_filename = request.path.replace('/', '_').strip('_') + '.log'
        log_file_path = os.path.join(LOG_DIR, log_filename)
        
        # 追加写入日志
        with open(log_file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_data, ensure_ascii=False) + '\n')

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    @app.get("/health")
    def health():
        return jsonify({"ok": True}), 200

    return app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("API_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("API_PORT", "443")))
    parser.add_argument("--cn", default=os.environ.get("API_CERT_CN", "localhost"))
    parser.add_argument("--gen-certs-only", action="store_true")
    args = parser.parse_args()

    cert_dir = os.path.join(BASE_PATH, CERT_DIR)
    cert_path, key_path, ca_cert_path = _ensure_ca_and_server_cert(cert_dir, args.cn)
    print(f"CA 证书路径: {ca_cert_path}")
    print(f"服务端证书路径: {cert_path}")
    print("如需消除浏览器不安全警告，请将 CA 证书导入系统信任列表后再访问。")

    if args.gen_certs_only:
        return

    app = create_app()
    app.run(host=args.host, port=args.port, ssl_context=(cert_path, key_path), threaded=True)


if __name__ == "__main__":
    main()
