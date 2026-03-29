#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报表管理模块
功能：多设备报表批量生成、并发导出、目录管理
作用：统一管理报表生成逻辑，支持多线程并行生成提高效率
使用原因：报表逻辑独立，便于扩展不同格式的报表导出需求
"""
import os
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.config.settings import BASE_PATH
from src.core.posture_analyzer import generate_daily_data_for_device
from src.utils.excel_exporter import export_daily_report


def get_output_dir():
    env_dir = os.environ.get("OUTPUT_DIR")
    if env_dir:
        return env_dir
    # 修改为 data/reports 目录
    return os.path.join(BASE_PATH, "data", "reports")


def export_daily_reports_concurrently(device_count=10, output_dir=None):
    target_dir = output_dir or get_output_dir()
    os.makedirs(target_dir, exist_ok=True)

    date_str = time.strftime("%Y%m%d")

    def _worker(dev_id):
        data_rows = generate_daily_data_for_device(dev_id)
        filename = f"daily_posture_device_{dev_id:02d}_{date_str}.xls"
        return dev_id, export_daily_report(data_rows, filename=filename, output_dir=target_dir)

    results = []
    errors = []

    with ThreadPoolExecutor(max_workers=device_count) as executor:
        futures = [executor.submit(_worker, dev_id) for dev_id in range(1, device_count + 1)]
        for fut in as_completed(futures):
            dev_id, (ok, payload) = fut.result()
            if ok:
                results.append((dev_id, payload))
            else:
                errors.append((dev_id, payload))

    results.sort(key=lambda x: x[0])
    errors.sort(key=lambda x: x[0])

    return len(errors) == 0, {"output_dir": target_dir, "files": results, "errors": errors}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device-count", type=int, default=10, help="Number of report files to generate")
    parser.add_argument("--output-dir", default=None, help="Custom output directory")
    args = parser.parse_args()

    ok, result = export_daily_reports_concurrently(device_count=args.device_count, output_dir=args.output_dir)
    if ok:
        print(result["output_dir"])
        for dev_id, file_path in result["files"]:
            print(f"device_{dev_id:02d}: {file_path}")
        return 0

    print("报表生成失败")
    for dev_id, error in result["errors"]:
        print(f"device_{dev_id:02d}: {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

