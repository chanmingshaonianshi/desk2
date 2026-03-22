#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
趋势图窗口
"""
import tkinter as tk
from tkinter import ttk
import random
from src.config.settings import DEVICE_COLORS, CHART_WINDOW_SIZE, CHART_TITLE_FONT, CHART_AXIS_FONT, CHART_HOUR_RANGE, CHART_MAX_RATIO
from src.core.posture_analyzer import calculate_daily_score


class ChartWindow:
    """趋势图窗口类"""
    def __init__(self, parent, history_data):
        self.parent = parent
        self.history_data = history_data
        self.current_device = tk.IntVar(value=1)
        
        self.chart_window = tk.Toplevel(parent)
        self.chart_window.title("趋势分析图 (8:00 - 24:00)")
        self.chart_window.geometry(CHART_WINDOW_SIZE)
        self.chart_window.configure(bg="white")
        
        self.setup_ui()
        self.update_chart()
        
    def setup_ui(self):
        """初始化UI"""
        # 标题
        self.title_label = tk.Label(self.chart_window, 
                                   text=f"全天压力偏差趋势 - 设备{self.current_device.get()}", 
                                   font=CHART_TITLE_FONT, 
                                   bg="white", 
                                   fg=DEVICE_COLORS[self.current_device.get()-1])
        self.title_label.pack(pady=(10, 5))
        
        # 全天评分标签
        self.score_label = tk.Label(self.chart_window, 
                                    text="全天综合评分: --", 
                                    font=("微软雅黑", 14, "bold"), 
                                    bg="white", 
                                    fg="#2ca02c")
        self.score_label.pack(pady=(0, 10))
        
        # 设备切换区域
        switch_frame = tk.Frame(self.chart_window, bg="white")
        switch_frame.pack(fill=tk.X, padx=20)
        
        # 上一台按钮
        prev_btn = tk.Button(switch_frame, text="< 上一台", font=("微软雅黑", 12), 
                            bg="#f0f2f5", command=self.prev_device, 
                            width=10, relief=tk.FLAT, bd=0, padx=10, pady=5)
        prev_btn.pack(side=tk.LEFT)
        
        # 设备选择下拉框
        device_options = [f"设备{i}" for i in range(1, 11)]
        self.device_var = tk.StringVar(value=device_options[0])
        self.device_menu = ttk.Combobox(switch_frame, textvariable=self.device_var, 
                                       values=device_options, state="readonly", 
                                       font=("微软雅黑", 12), width=15)
        self.device_menu.pack(side=tk.LEFT, padx=20)
        self.device_menu.bind("<<ComboboxSelected>>", self.on_device_select)
        
        # 下一台按钮
        next_btn = tk.Button(switch_frame, text="下一台 >", font=("微软雅黑", 12), 
                            bg="#f0f2f5", command=self.next_device, 
                            width=10, relief=tk.FLAT, bd=0, padx=10, pady=5)
        next_btn.pack(side=tk.LEFT)
        
        # 画布
        self.cv_w, self.cv_h = 800, 450
        self.cv = tk.Canvas(self.chart_window, width=self.cv_w, height=self.cv_h, 
                           bg="white", highlightthickness=0)
        self.cv.pack(pady=20)
        
    def draw_axes(self):
        """绘制坐标轴"""
        m_l, m_r, m_t, m_b = 60, 40, 30, 50
        draw_w = self.cv_w - m_l - m_r
        draw_h = self.cv_h - m_t - m_b
        
        # 绘制Y轴
        self.cv.create_line(m_l, m_t, m_l, self.cv_h - m_b, width=2)
        for i in range(0, CHART_MAX_RATIO + 1, 4):
            y_pos = (self.cv_h - m_b) - (i / CHART_MAX_RATIO * draw_h)
            self.cv.create_line(m_l - 5, y_pos, m_l, y_pos, width=1)
            self.cv.create_text(m_l - 10, y_pos, text=f"{i}%", anchor="e", font=CHART_AXIS_FONT)
            if i > 0:
                self.cv.create_line(m_l, y_pos, self.cv_w - m_r, y_pos, fill="#f0f0f0", dash=(4, 4))

        # 绘制X轴
        x_step = draw_w / (len(CHART_HOUR_RANGE) - 1)
        self.cv.create_line(m_l, self.cv_h - m_b, self.cv_w - m_r, self.cv_h - m_b, width=2)
        for i, h in enumerate(CHART_HOUR_RANGE):
            x_pos = m_l + i * x_step
            self.cv.create_line(x_pos, self.cv_h - m_b, x_pos, self.cv_h - m_b + 5, width=1)
            self.cv.create_text(x_pos, self.cv_h - m_b + 15, text=f"{h}:00", font=("Arial", 8))
        
        return draw_w, draw_h, x_step
    
    def update_chart(self):
        """更新图表内容"""
        # 清空画布
        self.cv.delete("all")
        dev_id = self.current_device.get()
        color = DEVICE_COLORS[dev_id-1]
        
        # 更新标题
        self.title_label.config(text=f"全天压力偏差趋势 - 设备{dev_id}", fg=color)
        self.device_var.set(f"设备{dev_id}")
        
        # 绘制坐标轴
        draw_w, draw_h, x_step = self.draw_axes()
        
        # 准备数据点并计算评分
        points = []
        total_ratio = 0
        count = 0
        
        m_l, m_r, m_t, m_b = 60, 40, 30, 50
        
        for i in range(len(CHART_HOUR_RANGE)):
            # 如果有历史数据则用历史，否则模拟
            if dev_id in self.history_data and i < len(self.history_data[dev_id]):
                ratio_val = self.history_data[dev_id][i]['ratio'] * 100
            else:
                ratio_val = random.uniform(0, 35)
            
            # 累加用于计算平均值
            total_ratio += ratio_val
            count += 1
                
            x = m_l + i * x_step
            y = (self.cv_h - m_b) - (ratio_val / CHART_MAX_RATIO * draw_h)
            points.append((x, y))
        
        # 计算并显示全天评分
        avg_ratio = total_ratio / count if count > 0 else 0
        score = calculate_daily_score(avg_ratio)
        
        score_color = "#2ca02c"  # 绿色
        if score < 90: score_color = "#ff7f0e"  # 橙色
        if score < 60: score_color = "#d62728"  # 红色
        
        self.score_label.config(text=f"全天综合评分: {score} 分 (平均偏差 {avg_ratio:.1f}%)", fg=score_color)
        
        # 绘制曲线和数据点
        for j in range(len(points) - 1):
            self.cv.create_line(points[j][0], points[j][1], points[j+1][0], points[j+1][1], 
                               fill=color, width=3, capstyle=tk.ROUND, joinstyle=tk.ROUND)
        for x, y in points:
            self.cv.create_oval(x-4, y-4, x+4, y+4, fill=color, outline=color)
    
    def prev_device(self):
        """切换到上一台设备"""
        dev = self.current_device.get()
        if dev > 1:
            self.current_device.set(dev - 1)
            self.update_chart()
    
    def next_device(self):
        """切换到下一台设备"""
        dev = self.current_device.get()
        if dev < 10:
            self.current_device.set(dev + 1)
            self.update_chart()
    
    def on_device_select(self, event):
        """下拉框选择设备"""
        selected = self.device_var.get()
        dev_id = int(selected.replace("设备", ""))
        self.current_device.set(dev_id)
        self.update_chart()
