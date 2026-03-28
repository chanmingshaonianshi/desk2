#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API接口自动化测试脚本
功能：逐个测试所有API接口，验证功能正常
使用方法：运行脚本即可自动完成所有接口测试
"""
import os
import sys
import uuid
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config.settings import API_APP_ID, API_APP_SECRET, BASE_PATH

# 测试配置
BASE_URL = "https://127.0.0.1:443"
VERIFY_SSL = False

def test_health():
    """测试健康检查接口"""
    print("\n=== 测试健康检查接口 GET /health ===")
    try:
        resp = requests.get(f"{BASE_URL}/health", verify=VERIFY_SSL, timeout=5)
        assert resp.status_code == 200, f"状态码错误：{resp.status_code}"
        assert resp.json()["ok"] == True, "响应内容错误"
        print("✅ 健康检查接口测试通过")
        return True
    except Exception as e:
        print(f"❌ 健康检查接口测试失败：{e}")
        return False

def test_login():
    """测试登录接口"""
    print("\n=== 测试登录接口 POST /login ===")
    try:
        # 正常登录
        resp = requests.post(
            f"{BASE_URL}/login",
            json={"app_id": API_APP_ID, "app_secret": API_APP_SECRET},
            verify=VERIFY_SSL,
            timeout=5
        )
        assert resp.status_code == 200, f"状态码错误：{resp.status_code}"
        data = resp.json()
        assert data["ok"] == True, "响应内容错误"
        assert "token" in data, "缺少token字段"
        assert data["token_type"] == "Bearer", "token_type错误"
        token = data["token"]
        print("✅ 登录接口测试通过")
        
        # 错误密码测试
        resp = requests.post(
            f"{BASE_URL}/login",
            json={"app_id": API_APP_ID, "app_secret": "wrong_secret"},
            verify=VERIFY_SSL,
            timeout=5
        )
        assert resp.status_code == 403, "错误密码应返回403"
        print("✅ 错误密码鉴权测试通过")
        
        # 缺少参数测试
        resp = requests.post(
            f"{BASE_URL}/login",
            json={"app_id": API_APP_ID},
            verify=VERIFY_SSL,
            timeout=5
        )
        assert resp.status_code == 400, "缺少参数应返回400"
        print("✅ 缺少参数校验测试通过")
        
        return token
    except Exception as e:
        print(f"❌ 登录接口测试失败：{e}")
        return None

def test_upload(token):
    """测试上传接口"""
    print("\n=== 测试上传接口 POST /api/v1/upload ===")
    if not token:
        print("❌ 跳过上传测试：未获取到token")
        return False
        
    try:
        headers = {"Authorization": f"Bearer {token}"}
        request_id = str(uuid.uuid4())
        payload = {
            "request_id": request_id,
            "device_id": "device_001",
            "timestamp": 1700000000000,
            "sensors": {
                "left_force_n": 300.0,
                "right_force_n": 280.0
            },
            "analysis": {
                "deviation_ratio": 0.034
            }
        }
        
        # 首次上传
        resp = requests.post(
            f"{BASE_URL}/api/v1/upload",
            json=payload,
            headers=headers,
            verify=VERIFY_SSL,
            timeout=5
        )
        assert resp.status_code == 202, f"首次上传状态码错误：{resp.status_code}"
        data = resp.json()
        assert data["ok"] == True, "响应内容错误"
        assert data["request_id"] == request_id, "request_id不匹配"
        print("✅ 首次上传测试通过")
        
        # 重复上传（幂等测试）
        resp = requests.post(
            f"{BASE_URL}/api/v1/upload",
            json=payload,
            headers=headers,
            verify=VERIFY_SSL,
            timeout=5
        )
        assert resp.status_code == 200, f"重复上传应返回200，实际返回：{resp.status_code}"
        print("✅ 幂等性测试通过")
        
        # 缺少request_id测试
        payload_invalid = payload.copy()
        del payload_invalid["request_id"]
        resp = requests.post(
            f"{BASE_URL}/api/v1/upload",
            json=payload_invalid,
            headers=headers,
            verify=VERIFY_SSL,
            timeout=5
        )
        assert resp.status_code == 400, "缺少request_id应返回400"
        print("✅ 参数校验测试通过")
        
        # 无效token测试
        headers_invalid = {"Authorization": "Bearer invalid_token"}
        resp = requests.post(
            f"{BASE_URL}/api/v1/upload",
            json=payload,
            headers=headers_invalid,
            verify=VERIFY_SSL,
            timeout=5
        )
        assert resp.status_code == 403, "无效token应返回403"
        print("✅ 鉴权校验测试通过")
        
        # 兼容接口测试
        resp = requests.post(
            f"{BASE_URL}/api/upload_data",
            json=payload,
            headers=headers,
            verify=VERIFY_SSL,
            timeout=5
        )
        assert resp.status_code in [200, 202], f"兼容接口状态码错误：{resp.status_code}"
        print("✅ 旧版本兼容接口测试通过")
        
        return True
    except Exception as e:
        print(f"❌ 上传接口测试失败：{e}")
        return False

def main():
    print("="*50)
    print("Moon_Dance API 接口自动化测试")
    print("="*50)
    
    # 运行所有测试
    tests_passed = 0
    tests_total = 3
    
    # 测试1：健康检查
    if test_health():
        tests_passed +=1
    
    # 测试2：登录
    token = test_login()
    if token:
        tests_passed +=1
    
    # 测试3：上传
    if test_upload(token):
        tests_passed +=1
    
    # 测试结果汇总
    print("\n" + "="*50)
    print(f"测试完成：{tests_passed}/{tests_total} 个接口测试通过")
    print("="*50)
    
    if tests_passed == tests_total:
        print("🎉 所有接口测试全部通过！")
        return 0
    else:
        print("⚠️  部分接口测试失败，请检查问题")
        return 1

if __name__ == "__main__":
    sys.exit(main())
