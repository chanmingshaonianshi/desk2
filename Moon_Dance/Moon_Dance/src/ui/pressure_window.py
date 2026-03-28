#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
压力曲面显示窗口
"""
import tkinter as tk
from tkinter import ttk
import time
from src.config.settings import DEVICE_COLORS
from src.core.pressure_surface import generate_pressure_surface, pressure_to_color
from src.core.posture_analyzer import generate_force_data, calculate_ratio, get_assessment, calculate_daily_score


class PressureSurfaceWindow:
    """压力曲面窗口类"""
    def __init__(self, parent):
        self.parent = parent
        self.current_device = tk.IntVar(value=1)
        self.is_running = True
        self.auto_update = tk.BooleanVar(value=True)
        
        self.window = tk.Toplevel(parent)
        self.window.title("实时压力曲面监测")
        self.window.geometry("750x700")
        self.window.configure(bg="#f0f2f5")
        
        # 窗口关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 曲线窗口引用
        self.curve_window = None
        self.chart_canvas_x = None
        self.chart_canvas_y = None
        
        self.setup_ui()
        self.update_surface()
        
    def setup_ui(self):
        """初始化UI"""
        # 标题
        title_label = tk.Label(self.window, text="实时压力曲面监测", 
                              font=("微软雅黑", 18, "bold"), 
                              bg="#f0f2f5", fg="#1a73e8")
        title_label.pack(pady=10)
        
        # 设备切换区域
        switch_frame = tk.Frame(self.window, bg="#f0f2f5")
        switch_frame.pack(fill=tk.X, padx=30)
        
        # 设备选择
        tk.Label(switch_frame, text="当前设备:", font=("微软雅黑", 12), 
                bg="#f0f2f5").pack(side=tk.LEFT, padx=5)
        
        device_options = [f"设备{i}" for i in range(1, 11)]
        self.device_var = tk.StringVar(value=device_options[0])
        self.device_menu = ttk.Combobox(switch_frame, textvariable=self.device_var, 
                                       values=device_options, state="readonly", 
                                       font=("微软雅黑", 12), width=12)
        self.device_menu.pack(side=tk.LEFT, padx=10)
        self.device_menu.bind("<<ComboboxSelected>>", self.on_device_select)
        
        # 自动更新开关
        auto_check = tk.Checkbutton(switch_frame, text="5秒自动更新", 
                                   variable=self.auto_update, font=("微软雅黑", 12),
                                   bg="#f0f2f5", activebackground="#f0f2f5")
        auto_check.pack(side=tk.LEFT, padx=20)
        
        # 手动更新按钮
        update_btn = tk.Button(switch_frame, text="立即刷新", font=("微软雅黑", 12), 
                              bg="#1a73e8", fg="white", command=self.update_surface,
                              relief=tk.FLAT, bd=0, padx=15, pady=5,
                              activebackground="#2d8bf2", activeforeground="white")
        update_btn.pack(side=tk.RIGHT)
        
        # 压力曲面画布
        self.canvas_size = 480
        self.cell_size = self.canvas_size // 32  # 32x32网格
        self.canvas = tk.Canvas(self.window, width=self.canvas_size, height=self.canvas_size, 
                               bg="white", highlightthickness=1, highlightbackground="#ccc")
        self.canvas.pack(pady=20)
        
        # 信息面板
        info_frame = tk.Frame(self.window, bg="#f0f2f5")
        info_frame.pack(fill=tk.X, padx=30, pady=10)
        
        # 状态信息
        self.status_label = tk.Label(info_frame, text="状态: 坐姿端正", 
                                    font=("微软雅黑", 14, "bold"), fg="#2ca02c",
                                    bg="#f0f2f5")
        self.status_label.pack(side=tk.LEFT)
        
        self.pressure_label = tk.Label(info_frame, text="左侧: 0N | 右侧: 0N | 偏差: 0.0%", 
                                      font=("微软雅黑", 12), bg="#f0f2f5")
        self.pressure_label.pack(side=tk.RIGHT)
        
        # 实时评分
        self.score_label = tk.Label(info_frame, text="实时评分: 100", 
                                    font=("微软雅黑", 14, "bold"), fg="#1a73e8",
                                    bg="#f0f2f5")
        self.score_label.pack(side=tk.RIGHT, padx=20)
        
        # 颜色条
        self.draw_color_bar()
        
        # 曲线显示按钮 (底部)
        btn_frame = tk.Frame(self.window, bg="#f0f2f5")
        btn_frame.pack(fill=tk.X, pady=10)
        
        curve_btn = tk.Button(btn_frame, text="显示压力分布曲线", font=("微软雅黑", 14, "bold"), 
                              bg="#9b59b6", fg="white", command=self.show_distribution_curves,
                              relief=tk.FLAT, bd=0, padx=30, pady=10,
                              activebackground="#b07cc6", activeforeground="white")
        curve_btn.pack()
        
    def draw_color_bar(self):
        """绘制压力颜色对照表"""
        bar_frame = tk.Frame(self.window, bg="#f0f2f5")
        bar_frame.pack(fill=tk.X, padx=30, pady=5)
        
        tk.Label(bar_frame, text="压力等级:", font=("微软雅黑", 10), 
                bg="#f0f2f5").pack(side=tk.LEFT, padx=5)
        
        bar_width = 200
        bar_height = 20
        bar_canvas = tk.Canvas(bar_frame, width=bar_width, height=bar_height, 
                              bg="white", highlightthickness=0)
        bar_canvas.pack(side=tk.LEFT, padx=5)
        
        # 绘制渐变条
        for i in range(bar_width):
            pressure = (i / bar_width) * 500
            color = pressure_to_color(pressure)
            bar_canvas.create_line(i, 0, i, bar_height, fill=color, width=1)
        
        # 刻度
        tk.Label(bar_frame, text="0N", font=("微软雅黑", 9), bg="#f0f2f5").pack(side=tk.LEFT, padx=2)
        tk.Label(bar_frame, text="250N", font=("微软雅黑", 9), bg="#f0f2f5").pack(side=tk.LEFT, padx=70)
        tk.Label(bar_frame, text="500N", font=("微软雅黑", 9), bg="#f0f2f5").pack(side=tk.LEFT, padx=2)
        
    def update_surface(self):
        """更新压力曲面"""
        if not self.is_running:
            return
            
        dev_id = self.current_device.get()
        # 生成符合当前左右压力比例的压力数据
        f_left, f_right = generate_force_data()
        ratio = calculate_ratio(f_left, f_right)
        status_text, status_tag = get_assessment(ratio)
        
        # 计算实时评分
        score = calculate_daily_score(ratio * 100)
        
        # 生成压力曲面
        surface = generate_pressure_surface(f_left, f_right)
        self.latest_surface = surface  # 保存最新数据
        
        # 绘制曲面
        self.canvas.delete("all")
        for y in range(32):
            for x in range(32):
                pressure = surface[y][x]
                color = pressure_to_color(pressure)
                x1 = x * self.cell_size
                y1 = y * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
        
        # 更新信息
        status_colors = {"normal": "#2ca02c", "orange": "#ff7f0e", "red_bold": "#d62728"}
        self.status_label.config(text=f"状态: {status_text}", fg=status_colors[status_tag])
        self.pressure_label.config(text=f"左侧: {f_left:.1f}N | 右侧: {f_right:.1f}N | 偏差: {ratio*100:.1f}%")
        
        # 更新评分显示
        score_color = "#2ca02c"  # 绿色
        if score < 90: score_color = "#ff7f0e"  # 橙色
        if score < 60: score_color = "#d62728"  # 红色
        self.score_label.config(text=f"实时评分: {score}", fg=score_color)
        
        self.device_var.set(f"设备{dev_id}")
        
        # 更新曲线图表
        self.update_charts_data(surface)
        
        # 自动更新
        if self.auto_update.get():
            self.window.after(5000, self.update_surface)
    
    def on_device_select(self, event):
        """切换设备"""
        selected = self.device_var.get()
        dev_id = int(selected.replace("设备", ""))
        if dev_id == self.current_device.get():
            return
        self.current_device.set(dev_id)
        self.update_surface()
    
    def on_close(self):
        """窗口关闭"""
        self.is_running = False
        if self.curve_window and self.curve_window.winfo_exists():
            self.curve_window.destroy()
        self.window.destroy()

    def show_distribution_curves(self):
        """显示压力分布曲线窗口"""
        if self.curve_window and self.curve_window.winfo_exists():
            self.curve_window.lift()
            return
            
        self.curve_window = tk.Toplevel(self.window)
        self.curve_window.title("压力分布曲线 (X/Y轴)")
        self.curve_window.geometry("800x600")
        self.curve_window.configure(bg="#f0f2f5")
        
        # X轴分布画布
        tk.Label(self.curve_window, text="X 轴压力分布趋势 (沿宽度方向)", 
                 font=("微软雅黑", 12, "bold"), bg="#f0f2f5").pack(pady=(10, 5))
        
        self.chart_canvas_x = tk.Canvas(self.curve_window, bg="white", height=220, 
                                       highlightthickness=1, highlightbackground="#ccc")
        self.chart_canvas_x.pack(fill=tk.X, padx=20, pady=5)
        
        # Y轴分布画布
        tk.Label(self.curve_window, text="Y 轴压力分布趋势 (沿深度方向)", 
                 font=("微软雅黑", 12, "bold"), bg="#f0f2f5").pack(pady=(10, 5))
        
        self.chart_canvas_y = tk.Canvas(self.curve_window, bg="white", height=220, 
                                       highlightthickness=1, highlightbackground="#ccc")
        self.chart_canvas_y.pack(fill=tk.X, padx=20, pady=5)
        
        # 如果有数据，立即更新
        if hasattr(self, 'latest_surface'):
            self.update_charts_data(self.latest_surface)

    def draw_curve(self, canvas, data, color, max_val=100):
        """在Canvas上绘制曲线"""
        if not canvas or not canvas.winfo_exists():
            return
            
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        # 如果窗口还未显示完全，宽度可能为1
        if w < 10: w = 760 
        if h < 10: h = 220
        
        canvas.delete("all")
        
        # 绘制坐标轴
        margin = 30
        draw_w = w - 2 * margin
        draw_h = h - 2 * margin
        
        # Y轴
        canvas.create_line(margin, margin, margin, h - margin, fill="black", width=1)
        # X轴
        canvas.create_line(margin, h - margin, w - margin, h - margin, fill="black", width=1)
        
        # 绘制30kPa警戒线 (假设最大量程为60kPa来绘图，或者自适应)
        # 这里为了视觉效果，固定量程 0-60kPa
        y_max_scale = 60.0
        
        warn_y = h - margin - (30 / y_max_scale) * draw_h
        canvas.create_line(margin, warn_y, w - margin, warn_y, fill="red", dash=(4, 4), width=2)
        canvas.create_text(w - margin + 5, warn_y, text="30kPa", fill="red", anchor="w", font=("Arial", 8))
        
        # 绘制数据
        if not data:
            return
            
        step_x = draw_w / (len(data) - 1)
        
        points = []
        for i, val in enumerate(data):
            x = margin + i * step_x
            # 限制显示范围
            if val > y_max_scale: val = y_max_scale
            y = h - margin - (val / y_max_scale) * draw_h
            points.append((x, y))
            
        if len(points) > 1:
            canvas.create_line(points, fill=color, width=2, smooth=True)
            
            # 绘制点
            for x, y in points:
                canvas.create_oval(x-2, y-2, x+2, y+2, fill=color, outline=color)

    def update_charts_data(self, surface):
        """更新图表数据"""
        if not surface or not self.curve_window or not self.curve_window.winfo_exists():
            return
            
        try:
            # 计算分布数据
            # X轴分布: 每一列的最大值
            cols = list(zip(*surface))
            x_dist = [max(col) for col in cols]
            
            # Y轴分布: 每一行的最大值
            y_dist = [max(row) for row in surface]
            
            # 绘制
            self.draw_curve(self.chart_canvas_x, x_dist, '#1f77b4')
            self.draw_curve(self.chart_canvas_y, y_dist, '#ff7f0e')
            
        except Exception as e:
            print(f"Error updating charts: {e}")
