#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
坐垫压力监测模拟系统
入口文件
"""
import argparse
import sys
import traceback
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed


def run_no_gui(device_count=10, duration=0):
    import time
    from simulator.core.device_simulator import DeviceSimulator
    from simulator.utils.json_db import append_record, append_realtime_log
    from simulator.core.report_manager import export_daily_reports_concurrently

    msg_queue = queue.Queue()

    print(f"--- 启动 {device_count} 路并发模拟 (No-GUI Mode) ---")
    print(f"--- 数据将保存至 ./data/ 目录 ---")
    if duration > 0:
        print(f"--- 计划运行时间: {duration} 秒 ---")
    print("按 Ctrl+C 停止模拟并生成报表...")

    def _worker(dev_id):
        simulator = DeviceSimulator(dev_id, msg_queue)
        record = simulator.measure()
        
        # 实时日志输出 (模拟终端数据跳动)
        log_msg = f"[{record['time']}] [Dev {dev_id:02d}] L:{record['f_left']:.1f} R:{record['f_right']:.1f} Ratio:{record['ratio']*100:.1f}%"
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
            
            # 模拟采样间隔
            time.sleep(1)
            
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
        args, _unknown = parser.parse_known_args()

        # 延迟导入以捕获依赖缺失错误
        if args.no_gui:
            run_no_gui(device_count=args.device_count, duration=args.duration)
            return

        from simulator.ui.main_window import CushionSimulatorApp
        
        app = CushionSimulatorApp()
        app.run()
    except ImportError as e:
        print("启动失败：缺少必要依赖库")
        print(f"错误详情: {e}")
        
        # 尝试提取缺失的模块名
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
        
        input("按回车键退出...")
        if not any(arg in sys.argv for arg in ["--no-gui"]):
            input("按回车键退出...")
        print("程序运行错误：")
        print(traceback.format_exc())
        input("按回车键退出...")
        if not any(arg in sys.argv for arg in ["--no-gui"]):
            input("按回车键退出...")
if __name__ == "__main__":
    main()
