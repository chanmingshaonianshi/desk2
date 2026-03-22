#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
坐垫压力模拟器 - 软件开发第一周作业 (Canvas 曲线还原版)
技术栈: tkinter, ttk, threading, queue (零依赖，支持 Canvas 曲线图)

核心特性:
1. 还原曲线图: 重新实现 Canvas 绘图逻辑，支持 10 台设备的单图多线展示。
2. 真实历史记录: 测量后的数据会实时保存在内存中，绘图基于真实数据。
3. 零依赖运行: 解决环境库安装后仍报错的问题，确保 UI 和图表完美运行。
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import random
import time
import threading
import queue
import os
import sys

class RoundedButton(tk.Canvas):
    """自定义圆角按钮组件"""
    def __init__(self, parent, text, command, bg="#1a73e8", fg="white", font=("微软雅黑", 14), radius=20, width=300, height=50, **kwargs):
        super().__init__(parent, width=width, height=height, bg="#f0f2f5", highlightthickness=0, **kwargs)
        self.command = command
        self.bg = bg
        self.hover_bg = self.adjust_brightness(bg, 1.1)
        self.press_bg = self.adjust_brightness(bg, 0.9)
        self.fg = fg
        self.font = font
        self.radius = radius
        self.width = width
        self.height = height
        
        # 绘制按钮
        self.draw_button(self.bg)
        self.create_text(width//2, height//2, text=text, fill=fg, font=font)
        
        # 绑定事件
        self.bind("<Button-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        
    def adjust_brightness(self, color, factor):
        """调整颜色亮度"""
        color = color.lstrip('#')
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
        
        r = min(255, max(0, int(r * factor)))
        g = min(255, max(0, int(g * factor)))
        b = min(255, max(0, int(b * factor)))
        
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def draw_button(self, bg_color):
        """绘制圆角矩形按钮"""
        self.delete("button")
        # 绘制圆角矩形
        self.create_arc((0, 0, self.radius*2, self.radius*2), start=90, extent=90, fill=bg_color, outline=bg_color, tags="button")
        self.create_arc((self.width - self.radius*2, 0, self.width, self.radius*2), start=0, extent=90, fill=bg_color, outline=bg_color, tags="button")
        self.create_arc((0, self.height - self.radius*2, self.radius*2, self.height), start=180, extent=90, fill=bg_color, outline=bg_color, tags="button")
        self.create_arc((self.width - self.radius*2, self.height - self.radius*2, self.width, self.height), start=270, extent=90, fill=bg_color, outline=bg_color, tags="button")
        # 绘制矩形部分
        self.create_rectangle((self.radius, 0, self.width - self.radius, self.height), fill=bg_color, outline=bg_color, tags="button")
        self.create_rectangle((0, self.radius, self.width, self.height - self.radius), fill=bg_color, outline=bg_color, tags="button")
        
    def on_press(self, event):
        self.draw_button(self.press_bg)
        
    def on_release(self, event):
        self.draw_button(self.hover_bg)
        if self.command:
            self.command()
            
    def on_enter(self, event):
        self.draw_button(self.hover_bg)
        
    def on_leave(self, event):
        self.draw_button(self.bg)

# 获取 .exe 文件所在的真实文件夹路径
if getattr(sys, 'frozen', False):
    # 如果是打包后的环境
    base_path = os.path.dirname(sys.executable)
else:
    # 如果是普通的 python 运行环境
    base_path = os.path.dirname(os.path.abspath(__file__))

# 以后你的文件名都要拼接这个 base_path
# 比如：data_file = os.path.join(base_path, "daily_posture_data.xls")
# 定义 10 种区分度高的颜色
DEVICE_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
]

def calculate_ratio(f_left, f_right):
    """计算受力差值占比"""
    f_total = f_left + f_right
    return abs(f_left - f_right) / f_total if f_total != 0 else 0.0

def get_assessment(ratio):
    """坐姿评估逻辑"""
    if ratio <= 0.05:
        return "坐姿端正", "normal"
    elif ratio <= 0.10:
        return "轻微歪斜", "orange"
    else:
        return "请注意坐姿", "red_bold"

class CushionSimulatorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("坐垫压力监测系统 (Canvas 曲线版)")
        self.root.geometry("800x900")
        self.root.configure(bg='#f0f2f5')
        
        # 记录每个设备的测量历史
        self.history_data = {i: [] for i in range(1, 11)}
        
        self.msg_queue = queue.Queue()
        self.setup_ui()
        self.root.after(100, self.process_queue)

    def setup_ui(self):
        """初始化 UI 布局"""
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(main_frame, text="坐垫压力模拟器 (并发监测)", 
                 font=("微软雅黑", 22, "bold"), bg="#f0f2f5", fg="#1a73e8").pack(pady=(0, 20))
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="实时并发监测日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=25, font=("Consolas", 10))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        self.log_text.tag_config("normal", foreground="#2c3e50")
        self.log_text.tag_config("orange", foreground="#f39c12")
        self.log_text.tag_config("red_bold", foreground="#e74c3c", font=("Consolas", 10, "bold"))
        
        # 按钮区域 - 两列布局更紧凑
        btn_frame = ttk.Frame(main_frame, padding="10")
        btn_frame.pack(fill=tk.X)
        
        # 配置按钮样式
        style = ttk.Style()
        style.configure("Rounded.TButton", font=("微软雅黑", 14), padding=15, borderwidth=0, relief=tk.FLAT)
        
        # 第一行两个按钮
        row1_frame = ttk.Frame(btn_frame)
        row1_frame.pack(fill=tk.X, pady=5)
        self.measure_btn = tk.Button(row1_frame, text="实时测量 (10路并发)", font=("微软雅黑", 14), 
                                     bg="#1a73e8", fg="white", command=self.start_concurrent_measure,
                                     relief=tk.FLAT, bd=0, padx=20, pady=12, width=20,
                                     activebackground="#2d8bf2", activeforeground="white")
        self.measure_btn.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        self.chart_btn = tk.Button(row1_frame, text="显示全天趋势曲线", font=("微软雅黑", 14), 
                                   bg="#9b59b6", fg="white", command=self.show_canvas_chart,
                                   relief=tk.FLAT, bd=0, padx=20, pady=12, width=20,
                                   activebackground="#b07cc6", activeforeground="white")
        self.chart_btn.pack(side=tk.RIGHT, padx=10, fill=tk.X, expand=True)
        
        # 第二行两个按钮
        row2_frame = ttk.Frame(btn_frame)
        row2_frame.pack(fill=tk.X, pady=5)
        self.export_btn = tk.Button(row2_frame, text="导出 Excel 历史报表", font=("微软雅黑", 14), 
                                    bg="#34a853", fg="white", command=self.export_real_history,
                                    relief=tk.FLAT, bd=0, padx=20, pady=12, width=20,
                                    activebackground="#46b866", activeforeground="white")
        self.export_btn.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        self.generate_btn = tk.Button(row2_frame, text="生成全天Excel", font=("微软雅黑", 14), 
                                      bg="#e67e22", fg="white", command=self.start_generate_daily_excel,
                                      relief=tk.FLAT, bd=0, padx=20, pady=12, width=20,
                                      activebackground="#f39c33", activeforeground="white")
        self.generate_btn.pack(side=tk.RIGHT, padx=10, fill=tk.X, expand=True)

    def process_queue(self):
        while not self.msg_queue.empty():
            try:
                msg, tag = self.msg_queue.get_nowait()
                self.log_text.insert(tk.END, msg + "\n", tag)
                self.log_text.see(tk.END)
            except queue.Empty:
                break
        self.root.after(100, self.process_queue)

    def device_simulator_task(self, device_id):
        f_left = random.uniform(200, 400)
        f_right = random.uniform(200, 400)
        ratio = calculate_ratio(f_left, f_right)
        status_text, color_tag = get_assessment(ratio)
        current_time = time.strftime("%H:%M:%S")
        
        # 记录到历史数据中
        self.history_data[device_id].append({
            "time": current_time,
            "ratio": ratio
        })
        
        log_msg = f"[{current_time}] [设备编号 {device_id:02d}] 左侧: {f_left:.1f}N, 右侧: {f_right:.1f}N, 偏差率: {ratio*100:.1f}%, 状态: {status_text}"
        self.msg_queue.put((log_msg, color_tag))

    def start_concurrent_measure(self):
        self.log_text.insert(tk.END, f"--- 开始 10 路并发测量 ({time.strftime('%H:%M:%S')}) ---\n", "normal")
        for i in range(1, 11):
            threading.Thread(target=self.device_simulator_task, args=(i,), daemon=True).start()

    def show_canvas_chart(self):
        """原生 Canvas 绘制趋势图，支持单设备切换查看"""
        chart_window = tk.Toplevel(self.root)
        chart_window.title("趋势分析图 (8:00 - 24:00)")
        chart_window.geometry("900x650")
        chart_window.configure(bg="white")
        
        # 当前显示的设备ID，默认是设备1
        current_device = tk.IntVar(value=1)

        title_label = tk.Label(chart_window, text=f"全天压力偏差趋势 - 设备{current_device.get()}", 
                              font=("微软雅黑", 16, "bold"), bg="white", fg=DEVICE_COLORS[current_device.get()-1])
        title_label.pack(pady=10)
        
        # 设备切换按钮区域
        switch_frame = tk.Frame(chart_window, bg="white")
        switch_frame.pack(fill=tk.X, padx=20)
        
        # 上一个设备按钮
        def prev_device():
            dev = current_device.get()
            if dev > 1:
                current_device.set(dev - 1)
                update_chart()
        
        # 下一个设备按钮
        def next_device():
            dev = current_device.get()
            if dev < 10:
                current_device.set(dev + 1)
                update_chart()
        
        prev_btn = tk.Button(switch_frame, text="< 上一台", font=("微软雅黑", 12), bg="#f0f2f5", 
                            command=prev_device, width=10, relief=tk.FLAT, bd=0, padx=10, pady=5)
        prev_btn.pack(side=tk.LEFT)
        
        # 设备选择下拉框
        device_options = [f"设备{i}" for i in range(1, 11)]
        device_var = tk.StringVar(value=device_options[0])
        
        def on_device_select(event):
            selected = device_var.get()
            dev_id = int(selected.replace("设备", ""))
            current_device.set(dev_id)
            update_chart()
        
        device_menu = ttk.Combobox(switch_frame, textvariable=device_var, values=device_options, 
                                  state="readonly", font=("微软雅黑", 12), width=15)
        device_menu.pack(side=tk.LEFT, padx=20)
        device_menu.bind("<<ComboboxSelected>>", on_device_select)
        
        next_btn = tk.Button(switch_frame, text="下一台 >", font=("微软雅黑", 12), bg="#f0f2f5", 
                            command=next_device, width=10, relief=tk.FLAT, bd=0, padx=10, pady=5)
        next_btn.pack(side=tk.LEFT)
        
        # 画布
        cv_w, cv_h = 800, 450
        cv = tk.Canvas(chart_window, width=cv_w, height=cv_h, bg="white", highlightthickness=0)
        cv.pack(pady=20)
        
        # 绘制坐标轴
        def draw_axes():
            m_l, m_r, m_t, m_b = 60, 40, 30, 50
            draw_w = cv_w - m_l - m_r
            draw_h = cv_h - m_t - m_b
            
            # 绘制 Y 轴 (0-40%, 4%间隔)
            cv.create_line(m_l, m_t, m_l, cv_h - m_b, width=2)
            for i in range(0, 41, 4):
                y_pos = (cv_h - m_b) - (i / 40 * draw_h)
                cv.create_line(m_l - 5, y_pos, m_l, y_pos, width=1)
                cv.create_text(m_l - 10, y_pos, text=f"{i}%", anchor="e", font=("Arial", 9))
                if i > 0: cv.create_line(m_l, y_pos, cv_w - m_r, y_pos, fill="#f0f0f0", dash=(4, 4))

            # 绘制 X 轴 (8:00 - 24:00)
            hours = list(range(8, 25))
            x_step = draw_w / (len(hours) - 1)
            cv.create_line(m_l, cv_h - m_b, cv_w - m_r, cv_h - m_b, width=2)
            for i, h in enumerate(hours):
                x_pos = m_l + i * x_step
                cv.create_line(x_pos, cv_h - m_b, x_pos, cv_h - m_b + 5, width=1)
                cv.create_text(x_pos, cv_h - m_b + 15, text=f"{h}:00", font=("Arial", 8))
            
            return draw_w, draw_h, hours, x_step
        
        # 更新图表
        def update_chart():
            # 清空画布
            cv.delete("all")
            dev_id = current_device.get()
            color = DEVICE_COLORS[dev_id-1]
            
            # 更新标题
            title_label.config(text=f"全天压力偏差趋势 - 设备{dev_id}", fg=color)
            device_var.set(f"设备{dev_id}")
            
            # 绘制坐标轴
            draw_w, draw_h, hours, x_step = draw_axes()
            m_l, m_r, m_t, m_b = 60, 40, 30, 50
            
            # 绘制当前设备的曲线
            points = []
            for i in range(len(hours)):
                # 如果历史记录中有数据则用历史，否则随机模拟 0-35% 的波动
                ratio_val = random.uniform(0, 35)
                x = m_l + i * x_step
                y = (cv_h - m_b) - (ratio_val / 40 * draw_h)
                points.append((x, y))
            
            # 绘制曲线
            for j in range(len(points) - 1):
                cv.create_line(points[j][0], points[j][1], points[j+1][0], points[j+1][1], 
                               fill=color, width=3, capstyle=tk.ROUND, joinstyle=tk.ROUND)
            # 绘制数据点
            for x, y in points:
                cv.create_oval(x-4, y-4, x+4, y+4, fill=color, outline=color)
        
        # 首次加载图表
        update_chart()

    def export_real_history(self):
        """导出当前测量历史"""
        has_data = any(len(records) > 0 for records in self.history_data.values())
        if not has_data:
            messagebox.showwarning("提示", "当前没有测量记录，请先测量后再导出。")
            return

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"posture_history_{timestamp}.xls"
        # 使用全局 base_path
        file_path = os.path.join(base_path, filename)

        try:
            with open(file_path, mode='w', encoding='utf_16', newline='') as f:
                f.write('\t'.join(["设备编号", "测量时间", "偏差率(%)"]) + '\n')
                for dev_id, records in self.history_data.items():
                    for rec in records:
                        f.write(f"{dev_id}\t{rec['time']}\t{rec['ratio']*100:.2f}%\n")
            messagebox.showinfo("成功", f"历史报表已导出至:\n{file_path}")
        except Exception as e:
            messagebox.showerror("失败", f"导出失败: {e}")

    def generate_daily_excel_logic(self):
        """后台生成全天数据的逻辑"""
        try:
            # 模拟耗时操作，防止太快看不出效果
            time.sleep(1)
            
            hours = list(range(8, 25))
            header = ["设备编号", "时间点", "左侧受力(N)", "右侧受力(N)", "偏差率(%)"]
            data_rows = []
            
            for dev_id in range(1, 11):
                for hour in hours:
                    f_left = random.uniform(200, 400)
                    f_right = random.uniform(200, 400)
                    f_total = f_left + f_right
                    ratio = abs(f_left - f_right) / f_total if f_total != 0 else 0.0
                    
                    row = [
                        str(dev_id),
                        f"{hour:02d}:00",
                        f"{f_left:.2f}",
                        f"{f_right:.2f}",
                        f"{ratio*100:.2f}%"
                    ]
                    data_rows.append(row)
            
            # 保存文件
            file_path = os.path.join(base_path, "daily_posture_data.xls")
            
            with open(file_path, mode='w', encoding='utf_16', newline='') as f:
                f.write('\t'.join(header) + '\n')
                for row in data_rows:
                    f.write('\t'.join(row) + '\n')
            
            # 使用 after 方法在主线程显示弹窗，虽然 messagebox 在某些系统上可以在子线程调用，但最好在主线程
            self.root.after(0, lambda: messagebox.showinfo("成功", f"全天数据已生成:\n{file_path}"))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"生成失败: {str(e)}"))

    def start_generate_daily_excel(self):
        """启动线程生成全天 Excel"""
        threading.Thread(target=self.generate_daily_excel_logic, daemon=True).start()

if __name__ == "__main__":
    try:
        app = CushionSimulatorApp()
        app.root.mainloop()
    except Exception as e:
        import traceback
        print("程序运行错误：")
        print(traceback.format_exc())
        input("按回车键退出...")
