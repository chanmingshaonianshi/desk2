import os
import time
import random
import requests
import urllib3
"""
文件：simulate_clients.py
实现了什么：高并发多线程的传感器数据模拟器（HTTP 客户端）。
怎么实现的：使用 argparse 接收启动参数（并发数、目标 API 地址）。利用 concurrent.futures.ThreadPoolExecutor 创建多个线程，每个线程模拟一个物理设备，使用 requests 库构造包含 Bearer Token 和随机传感器数据的 JSON 负载，并循环向指定的后端接口发送 POST 请求（跳过 SSL 验证以适配本地测试和自定义域名）。
为什么实现：为了测试服务器在真实业务场景下的抗压能力（高并发处理能力），并在演示时制造真实的“多设备数据流”，直观展示前后端联调效果和负载均衡效果。
"""
import argparse
from concurrent.futures import ThreadPoolExecutor

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def send_data(device_id, api_url, token, interval):
    print(f"[{device_id}] Starting simulated client, targeting {api_url}")
    while True:
        try:
            f_left = random.uniform(10.0, 50.0)
            f_right = random.uniform(10.0, 50.0)
            ratio = abs(f_left - f_right) / (f_left + f_right) if (f_left + f_right) > 0 else 0
            
            payload = {
                "device_id": device_id,
                "timestamp": int(time.time() * 1000),
                "sensors": {
                    "left_force_n": round(f_left, 1),
                    "right_force_n": round(f_right, 1),
                    "total_force_n": round(f_left + f_right, 1)
                },
                "analysis": {
                    "deviation_ratio": round(ratio, 4)
                }
            }
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(api_url, json=payload, headers=headers, verify=False, timeout=5)
            print(f"[{device_id}] Sent data: {payload['sensors']} - Status: {response.status_code}")
        except Exception as e:
            print(f"[{device_id}] Error sending data: {e}")
        
        time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MoonDance Concurrent HTTP Simulated Clients.")
    parser.add_argument("-n", "--number", type=int, default=1, help="Number of simulated clients to run concurrently")
    parser.add_argument("--api-url", type=str, default=os.environ.get("API_URL", "https://www.myhjmycjh.tech:3006/api/v2/ingest"), help="Target API URL")
    parser.add_argument("--token", type=str, default=os.environ.get("TOKEN", "change_me_token"), help="Auth token")
    parser.add_argument("--interval", type=int, default=int(os.environ.get("INTERVAL", "5")), help="Interval in seconds between requests")
    args = parser.parse_args()

    print(f"Starting {args.number} simulated clients targeting {args.api_url}...")
    
    with ThreadPoolExecutor(max_workers=args.number) as executor:
        for i in range(1, args.number + 1):
            device_id = f"sim_device_{i:03d}"
            # Add a slight random delay so they don't all hit exactly at the same millisecond initially
            time.sleep(random.uniform(0.1, 1.0))
            executor.submit(send_data, device_id, args.api_url, args.token, args.interval)

