#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel导出工具
"""
import os
import time
from src.config.settings import BASE_PATH
from src.core.posture_analyzer import calculate_daily_score


def _get_messagebox():
    try:
        from tkinter import messagebox
        return messagebox
    except Exception:
        return None


def export_history_data(history_data, filename=None, output_dir=None, show_messagebox=True):
    """导出历史测量数据到Excel"""
    has_data = any(len(records) > 0 for records in history_data.values())
    if not has_data:
        if show_messagebox:
            messagebox = _get_messagebox()
            if messagebox:
                messagebox.showwarning("提示", "当前没有测量记录，请先测量后再导出。")
        return False

    if not filename:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"posture_history_{timestamp}.xls"
    
    target_dir = output_dir or BASE_PATH
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, filename)

    try:
        with open(file_path, mode='w', encoding='utf_16', newline='') as f:
            f.write(f"导出时间:\t{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("\n")
            f.write('\t'.join(["设备编号", "测量时间", "偏差率(%)"]) + '\n')
            for dev_id, records in history_data.items():
                for rec in records:
                    f.write(f"{dev_id}\t{rec['time']}\t{rec['ratio']*100:.2f}%\n")
        if show_messagebox:
            messagebox = _get_messagebox()
            if messagebox:
                messagebox.showinfo("成功", f"历史报表已导出至:\n{file_path}")
        return True
    except Exception as e:
        if show_messagebox:
            messagebox = _get_messagebox()
            if messagebox:
                messagebox.showerror("失败", f"导出失败: {e}")
        return False


def export_daily_report(data_rows, filename="daily_posture_data.xls", output_dir=None):
    """导出全天数据报表"""
    target_dir = output_dir or BASE_PATH
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, filename)
    
    try:
        # 计算全天平均偏差率
        total_ratio = 0.0
        count = 0
        for row in data_rows:
            try:
                # row[4] 是 "XX.XX%" 格式的字符串
                ratio_str = row[4].replace('%', '')
                ratio_val = float(ratio_str)
                total_ratio += ratio_val
                count += 1
            except (ValueError, IndexError):
                continue
                
        avg_ratio = total_ratio / count if count > 0 else 0.0
        
        # 计算评分
        daily_score = calculate_daily_score(avg_ratio)

        header = ["设备编号", "时间点", "左侧受力(N)", "右侧受力(N)", "偏差率(%)"]
        with open(file_path, mode='w', encoding='utf_16', newline='') as f:
            f.write(f"报表生成时间:\t{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"今日坐姿评分:\t{daily_score}\n")
            f.write(f"平均偏差率:\t{avg_ratio:.2f}%\n")
            f.write("\n")
            
            f.write('\t'.join(header) + '\n')
            for row in data_rows:
                f.write('\t'.join(row) + '\n')
        return True, file_path
    except Exception as e:
        return False, str(e)
