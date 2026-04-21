#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地测试脚本，验证 MongoDB 连接与异步写入读取是否正常工作
此脚本只是用于您在控制台验证查阅，不参与主业务的运行。
"""
import time
import sys
from src.utils.json_db import append_realtime_log
from src.utils.mongo_db import get_latest_10_records

def main():
    print("===========================================")
    print("      MongoDB 数据链条测试脚本")
    print("===========================================\n")
    
    print("[1] 正在模拟生成一条测试压力数据...")
    test_record = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "device_id": "sim_test_001",
        "f_left": 150.5,
        "f_right": 148.2,
        "ratio": 0.05
    }
    
    print("[2] 正在将其投递到系统通用写入流程...")
    append_realtime_log(test_record)
    print("    ✅ 包含MongoDB异步分发在内的数据链正在后台运作")
    
    print("\n[3] 正在等待子线程写入并从 MongoDB 读取 (等待 1 秒)...\n")
    time.sleep(1) 
    
    print("------------ MongoDB 库内最近 10 条真实数据 --------------")
    records = get_latest_10_records()
    if not records:
        print("❌ 未找到任何数据，请检查 MongoDB 在 27017 端口是否正常运行及权限设置！")
        sys.exit(1)
        
    found_test_data = False
    for idx, r in enumerate(records, 1):
        device = r.get("device_id", "未知设备")
        left = r.get("f_left", 0)
        right = r.get("f_right", 0)
        t = r.get('time', "未知时间")
        
        print(f" {idx:02d}. [{t}] 设备: {device} | 压力 L/R: {left:.1f} / {right:.1f} | 数据库 ID: {r.get('_id')}")
        
        if device == "sim_test_001":
            found_test_data = True
            
    print("----------------------------------------------------------")
    
    if found_test_data:
        print("\n🎉 验证成功！刚才生成的模拟测试数据已经成功经由系统通道抵达 MongoDB 数据库！\n   您可以随时打开您的 Compass 直观地查看和分析表数据了。")
    else:
        print("\n⚠️ 发现记录，但没有找到刚才这秒钟插入的心跳测试数据，也许还在队列，或建议打开 Compass 手动确认。")

if __name__ == "__main__":
    main()
