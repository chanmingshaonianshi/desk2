#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import queue
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlsplit, urlunsplit


def _derive_login_url(api_url):
    if not api_url:
        return None
    parts = urlsplit(api_url)
    if not parts.scheme or not parts.netloc:
        return None
    return urlunsplit((parts.scheme, parts.netloc, "/login", "", ""))


def _resolve_api_token(api_token, api_url, login_url, verify_ssl):
    if api_token:
        return api_token
    target_login_url = login_url or _derive_login_url(api_url)
    if not target_login_url:
        return None

    import requests
    from src.config.settings import API_APP_ID, API_APP_SECRET

    response = requests.post(
        target_login_url,
        json={"app_id": API_APP_ID, "app_secret": API_APP_SECRET},
        timeout=5,
        verify=verify_ssl,
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("token")
    if not token:
        raise ValueError("登录接口未返回 token")
    print(f"--- 已自动获取上传 Token: {target_login_url} ---")
    return token


def run_no_gui(device_count=10, duration=0, interval=1.0, api_url=None, api_token=None, login_url=None, verify_ssl=True, use_mq=True):
    import time
    from src.core.device_simulator import DeviceSimulator
    from src.core.report_manager import export_daily_reports_concurrently
    from src.utils.json_db import append_record, append_realtime_log

    msg_queue = queue.Queue()
    resolved_token = _resolve_api_token(api_token, api_url, login_url, verify_ssl)

    print(f"--- 启动 {device_count} 路并发模拟 (No-GUI Mode) ---")
    print("--- 数据将保存至 ./data/ 目录 ---")
    if duration > 0:
        print(f"--- 计划运行时间: {duration} 秒 ---")
    if api_url:
        print(f"--- 上传目标: {api_url} ---")
    print(f"--- 采样间隔: {interval} 秒 ---")
    print("按 Ctrl+C 停止模拟并生成报表...")

    def _worker(dev_id):
        simulator = DeviceSimulator(
            dev_id,
            msg_queue,
            use_mq=use_mq,
            api_url=api_url,
            api_token=resolved_token,
            verify_ssl=verify_ssl,
        )
        record = simulator.measure()
        log_msg = f"[{record['time']}] [Dev {dev_id:02d}] L:{record['f_left']:.1f} R:{record['f_right']:.1f} Ratio:{record['ratio'] * 100:.1f}%"
        print(log_msg)
        append_record(dev_id, record)
        append_realtime_log(record)
        return dev_id

    start_time = time.time()

    try:
        while True:
            current_time = time.time()
            if duration > 0 and (current_time - start_time) > duration:
                print(f"\n已运行 {duration} 秒，自动停止...")
                break

            with ThreadPoolExecutor(max_workers=device_count) as executor:
                futures = [executor.submit(_worker, dev_id) for dev_id in range(1, device_count + 1)]
                for fut in as_completed(futures):
                    fut.result()

            time.sleep(max(interval, 0))

    except KeyboardInterrupt:
        print("\n捕获 Ctrl+C，正在停止模拟...")
    except Exception as e:
        print(f"\n运行出错: {e}")
        traceback.print_exc()
    finally:
        print("\n正在生成全天汇总报表 (10线程并发)...")
        ok, result = export_daily_reports_concurrently(device_count=device_count)
        if not ok:
            errors = result.get("errors") or []
            err_text = "\n".join([f"device_{dev_id:02d}: {err}" for dev_id, err in errors]) or "未知错误"
            print(f"并行报表生成失败:\n{err_text}")
        else:
            output_dir = result.get("output_dir", "")
            print(f"10个设备报表已并行生成完毕，保存路径: {output_dir}")


def main():
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--no-gui", action="store_true", help="Run in headless mode without GUI")
        parser.add_argument("--device-count", type=int, default=10, help="Number of devices to simulate")
        parser.add_argument("--duration", type=int, default=0, help="Duration in seconds to run (0 for infinite)")
        parser.add_argument("--interval", type=float, default=1.0, help="Sampling interval in seconds")
        parser.add_argument("--api-url", default=None, help="Remote API endpoint for simulator uploads")
        parser.add_argument("--token", default=None, help="Bearer token for simulator uploads")
        parser.add_argument("--login-url", default=None, help="Login endpoint for auto fetching bearer token")
        parser.add_argument("--insecure", action="store_true", help="Disable SSL certificate verification for simulator uploads")
        parser.add_argument("--no-mq", action="store_true", help="Disable MQ publishing and only upload to API")
        args, _unknown = parser.parse_known_args()

        if args.no_gui:
            run_no_gui(
                device_count=args.device_count,
                duration=args.duration,
                interval=args.interval,
                api_url=args.api_url,
                api_token=args.token,
                login_url=args.login_url,
                verify_ssl=not args.insecure,
                use_mq=not args.no_mq,
            )
            return

        from src.ui.main_window import CushionSimulatorApp

        app = CushionSimulatorApp()
        app.run()
    except ImportError as e:
        print("启动失败：缺少必要依赖库")
        print(f"错误详情: {e}")

        missing_module = str(e)
        if "No module named" in missing_module:
            try:
                missing_module = missing_module.split("'")[1]
            except IndexError:
                pass

        print(f"\n当前环境缺少模块: {missing_module}")
        print("请尝试运行以下命令安装依赖：")
        print(f"pip install {missing_module}")
        print("或者安装所有依赖：")
        print("pip install -r requirements.txt")

        if not any(arg in sys.argv for arg in ["--no-gui"]):
            input("按回车键退出...")
    except Exception:
        print("程序运行错误：")
        print(traceback.format_exc())
        if not any(arg in sys.argv for arg in ["--no-gui"]):
            input("按回车键退出...")


if __name__ == "__main__":
    main()
