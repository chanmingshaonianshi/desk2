#!/usr/bin/env python3
import argparse
import json
import os
import time
from collections import deque

from src.config.settings import UPLOAD_LOG_FILE
from src.utils.json_db import REALTIME_LOG_FILE


def resolve_log_file(source, file_path):
    if file_path:
        return file_path
    if source == "upload":
        return UPLOAD_LOG_FILE
    return REALTIME_LOG_FILE


def normalize_record(record):
    sensors = record.get("sensors") or {}
    analysis = record.get("analysis") or {}
    timestamp = record.get("timestamp") or record.get("logged_at")
    if record.get("time"):
        display_time = str(record["time"])
    elif timestamp:
        display_time = time.strftime("%H:%M:%S", time.localtime(int(timestamp) / 1000))
    else:
        display_time = "--:--:--"

    ratio = record.get("ratio")
    if ratio is None:
        ratio = analysis.get("deviation_ratio", 0)
    try:
        ratio_text = f"{float(ratio) * 100:.1f}%"
    except Exception:
        ratio_text = "0.0%"

    left_force = record.get("f_left", sensors.get("left_force_n", 0))
    right_force = record.get("f_right", sensors.get("right_force_n", 0))
    try:
        left_text = f"{float(left_force):.1f}"
    except Exception:
        left_text = "0.0"
    try:
        right_text = f"{float(right_force):.1f}"
    except Exception:
        right_text = "0.0"

    status = (
        record.get("status")
        or analysis.get("assessment")
        or analysis.get("posture_status")
        or "--"
    )
    request_id = str(record.get("request_id", ""))
    return {
        "time": display_time,
        "device_id": str(record.get("device_id", "--")),
        "left": left_text,
        "right": right_text,
        "ratio": ratio_text,
        "status": str(status),
        "request_id": request_id[:8] if request_id else "--",
    }


def parse_json_lines(lines, rows):
    appended = 0
    for line in lines:
        raw = line.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        rows.append(normalize_record(payload))
        appended += 1
    return appended


def render_table(rows):
    headers = [
        ("time", "Time"),
        ("device_id", "Device"),
        ("left", "Left(N)"),
        ("right", "Right(N)"),
        ("ratio", "Ratio"),
        ("status", "Status"),
        ("request_id", "ReqID"),
    ]
    widths = {}
    for key, title in headers:
        widths[key] = len(title)
    for row in rows:
        for key, _title in headers:
            widths[key] = max(widths[key], len(str(row[key])))

    def format_row(row_map):
        return " | ".join(str(row_map[key]).ljust(widths[key]) for key, _title in headers)

    border = "-+-".join("-" * widths[key] for key, _title in headers)
    header_row = format_row({key: title for key, title in headers})
    body = [format_row(row) for row in rows]
    return "\n".join([header_row, border] + body) if body else "\n".join([header_row, border])


def read_recent_rows(file_path, rows, limit):
    if not os.path.exists(file_path):
        return
    with open(file_path, "r", encoding="utf-8") as file_obj:
        parse_json_lines(deque(file_obj, maxlen=limit), rows)


def print_snapshot(file_path, rows, source):
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {source} 监控: {file_path}")
    print(render_table(list(rows)))
    print(f"总显示条数: {len(rows)}")


def follow_file(file_path, rows, source, interval):
    position = 0
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file_obj:
            file_obj.seek(0, os.SEEK_END)
            position = file_obj.tell()

    while True:
        if not os.path.exists(file_path):
            print(f"等待日志文件出现: {file_path}")
            time.sleep(interval)
            continue

        with open(file_path, "r", encoding="utf-8") as file_obj:
            file_obj.seek(position)
            new_lines = file_obj.readlines()
            position = file_obj.tell()

        appended = parse_json_lines(new_lines, rows)
        if appended:
            print_snapshot(file_path, rows, source)
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["upload", "realtime"], default="upload")
    parser.add_argument("--file", default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--follow", action="store_true")
    args = parser.parse_args()

    file_path = resolve_log_file(args.source, args.file)
    rows = deque(maxlen=max(args.limit, 1))
    read_recent_rows(file_path, rows, max(args.limit, 1))
    print_snapshot(file_path, rows, args.source)

    if args.follow:
        try:
            follow_file(file_path, rows, args.source, max(args.interval, 0.1))
        except KeyboardInterrupt:
            print("\n已停止监控")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
