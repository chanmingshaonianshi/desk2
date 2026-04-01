#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
from collections import deque
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.settings import UPLOAD_LOG_FILE
from src.utils.json_db import REALTIME_LOG_FILE

IGNORED_PARAM_FIELDS = {"time", "ratio", "f_left", "f_right", "logged_at"}


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


def infer_type_name(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return type(value).__name__


def format_sample(value):
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    if len(text) > 36:
        return text[:33] + "..."
    return text


def flatten_payload(value, prefix=""):
    rows = []
    if isinstance(value, dict):
        for key, nested in value.items():
            field_name = f"{prefix}.{key}" if prefix else str(key)
            if field_name in IGNORED_PARAM_FIELDS:
                continue
            rows.extend(flatten_payload(nested, field_name))
        if prefix and not rows:
            rows.append((prefix, "dict", "{}"))
        return rows
    if isinstance(value, list):
        rows.append((prefix or "root", "list", f"len={len(value)}"))
        return rows
    rows.append((prefix or "root", infer_type_name(value), format_sample(value)))
    return rows


def extract_timestamp_ms(record):
    value = record.get("timestamp") or record.get("logged_at")
    try:
        return int(value)
    except Exception:
        return None


def build_param_rows(records):
    if not records:
        return []

    latest_record = records[-1]
    timestamps = [ts for ts in [extract_timestamp_ms(record) for record in records] if ts is not None]
    duration_seconds = 0.0
    if len(timestamps) >= 2:
        duration_seconds = max((max(timestamps) - min(timestamps)) / 1000.0, 0.0)

    field_stats = {}
    for record in records:
        seen_fields = set()
        for field_name, type_name, sample in flatten_payload(record):
            if field_name in IGNORED_PARAM_FIELDS:
                continue
            stats = field_stats.setdefault(field_name, {"type": type_name, "sample": sample, "count": 0})
            if field_name not in seen_fields:
                stats["count"] += 1
                seen_fields.add(field_name)

    latest_fields = {}
    for field_name, type_name, sample in flatten_payload(latest_record):
        if field_name in IGNORED_PARAM_FIELDS:
            continue
        latest_fields[field_name] = (type_name, sample)

    rows = []
    for field_name in sorted(field_stats):
        type_name, sample = latest_fields.get(field_name, (field_stats[field_name]["type"], field_stats[field_name]["sample"]))
        count = field_stats[field_name]["count"]
        if duration_seconds > 0:
            freq_text = f"{count / duration_seconds:.2f} Hz"
        else:
            freq_text = f"{count} 次/窗口"
        rows.append({
            "field": field_name,
            "type": type_name,
            "sample": sample,
            "frequency": freq_text,
        })
    return rows


def parse_json_lines(lines, rows, raw_records):
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
        raw_records.append(payload)
        appended += 1
    return appended


def render_table(rows, headers):
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


def transmission_headers():
    return [
        ("time", "Time"),
        ("device_id", "Device"),
        ("left", "Left(N)"),
        ("right", "Right(N)"),
        ("ratio", "Ratio"),
        ("status", "Status"),
        ("request_id", "ReqID"),
    ]


def parameter_headers():
    return [
        ("field", "Param"),
        ("type", "Type"),
        ("sample", "Sample"),
        ("frequency", "Frequency"),
    ]


def read_recent_rows(file_path, rows, raw_records, limit):
    if not os.path.exists(file_path):
        return
    with open(file_path, "r", encoding="utf-8") as file_obj:
        parse_json_lines(deque(file_obj, maxlen=limit), rows, raw_records)


def print_snapshot(file_path, rows, raw_records, source):
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {source} 监控: {file_path}")
    print("最近传输记录")
    print(render_table(list(rows), transmission_headers()))
    print(f"总显示条数: {len(rows)}")
    print("\nAPI参数表")
    print(render_table(build_param_rows(list(raw_records)), parameter_headers()))


def follow_file(file_path, rows, raw_records, source, interval):
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

        appended = parse_json_lines(new_lines, rows, raw_records)
        if appended:
            print_snapshot(file_path, rows, raw_records, source)
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
    raw_records = deque(maxlen=max(args.limit, 1))
    read_recent_rows(file_path, rows, raw_records, max(args.limit, 1))
    print_snapshot(file_path, rows, raw_records, args.source)

    if args.follow:
        try:
            follow_file(file_path, rows, raw_records, args.source, max(args.interval, 0.1))
        except KeyboardInterrupt:
            print("\n已停止监控")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
