#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import time
from src.config.settings import WINDOW_TITLE, WINDOW_SIZE, WINDOW_BG
from src.core.device_simulator import run_device_measurement
from src.core.report_manager import export_daily_reports_concurrently
from src.ui.chart_window import ChartWindow
from src.ui.pressure_window import PressureSurfaceWindow
from src.utils.excel_exporter import export_history_data
from src.utils.json_db import load_db, save_db, append_realtime_log


class CushionSimulatorApp:
    """主应用类"""
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.configure(bg=WINDOW_BG)
        
        # 历史数据存储 (从JSON数据库加载)
        self.history_data = load_db()
        self.msg_queue = queue.Queue()
        
        self.setup_ui()
        self.root.after(100, self.process_queue)

    def setup_ui(self):
        """初始化UI布局"""
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        tk.Label(main_frame, text="坐垫压力模拟器 (并发监测)", 
                 font=("微软雅黑", 22, "bold"), bg="#f0f2f5", fg="#1a73e8").pack(pady=(0, 20))
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="实时并发监测日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=25, font=("Consolas", 10))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 日志标签配置
        self.log_text.tag_config("normal", foreground="#2c3e50")
        self.log_text.tag_config("orange", foreground="#f39c12")
        self.log_text.tag_config("red_bold", foreground="#e74c3c", font=("Consolas", 10, "bold"))
        
        # 按钮区域 - 两列布局
        btn_frame = ttk.Frame(main_frame, padding="10")
        btn_frame.pack(fill=tk.X)
        
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
        
        # 第三行：压力曲面按钮（通栏）
        row3_frame = ttk.Frame(btn_frame)
        row3_frame.pack(fill=tk.X, pady=5)
        self.pressure_btn = tk.Button(row3_frame, text="实时压力曲面监测", font=("微软雅黑", 14), 
                                      bg="#17becf", fg="white", command=self.show_pressure_surface,
                                      relief=tk.FLAT, bd=0, padx=20, pady=12,
                                      activebackground="#2fc8d9", activeforeground="white")
        self.pressure_btn.pack(fill=tk.X, padx=10, expand=True)

    def process_queue(self):
        """处理消息队列"""
        while not self.msg_queue.empty():
            try:
                # 获取消息 (日志文本, 颜色标签, 设备ID, 数据记录)
                item = self.msg_queue.get_nowait()
                if len(item) == 4:
                    msg, tag, dev_id, record = item
                    
                    # 显示日志
                    self.log_text.insert(tk.END, msg + "\n", tag)
                    self.log_text.see(tk.END)
                    
                    # 更新内存数据
                    if dev_id in self.history_data:
                        self.history_data[dev_id].append(record)
                    else:
                        self.history_data[dev_id] = [record]
                    
                    # 保存到JSON数据库
                    # 注意: 每次写入整个文件可能在数据量大时变慢，但在本模拟场景下可接受
                    save_db(self.history_data)
                    append_realtime_log(record)
                elif len(item) == 2:
                    # 兼容旧格式 (如果有)
                    msg, tag = item
                    self.log_text.insert(tk.END, msg + "\n", tag)
                    self.log_text.see(tk.END)
                    
            except queue.Empty:
                break
        self.root.after(100, self.process_queue)

    def start_concurrent_measure(self):
        """开始10路并发测量"""
        self.log_text.insert(tk.END, f"--- 开始 10 路并发测量 ({time.strftime('%H:%M:%S')}) ---\n", "normal")
        for i in range(1, 11):
            threading.Thread(target=run_device_measurement, 
                           args=(i, self.msg_queue), 
                           daemon=True).start()

    def show_canvas_chart(self):
        """显示趋势图窗口"""
        ChartWindow(self.root, self.history_data)
        
    def show_pressure_surface(self):
        """显示压力曲面窗口"""
        PressureSurfaceWindow(self.root)

    def export_real_history(self):
        """导出历史数据"""
        export_history_data(self.history_data)

    def generate_daily_excel_logic(self):
        """生成全天Excel逻辑"""
        try:
            time.sleep(1)  # 模拟耗时
            success, result = export_daily_reports_concurrently(device_count=10)
            if success:
                output_dir = result["output_dir"]
                self.root.after(0, lambda: messagebox.showinfo("成功", f"10个设备报表已并行生成完毕:\n{output_dir}"))
            else:
                errors = result.get("errors") or []
                err_text = "\n".join([f"device_{dev_id:02d}: {err}" for dev_id, err in errors]) or "未知错误"
                self.root.after(0, lambda: messagebox.showerror("错误", f"生成失败:\n{err_text}"))
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"生成失败: {str(e)}"))

    def start_generate_daily_excel(self):
        """启动线程生成全天Excel"""
        threading.Thread(target=self.generate_daily_excel_logic, daemon=True).start()

    def run(self):
        """运行应用"""
        self.root.mainloop()
