#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
臀部压力曲面生成算法
符合人体臀部压力分布生物学特征
无numpy依赖，纯Python实现
"""
import math
import random


def generate_pressure_surface(f_left, f_right, grid_size=32):
    """
    生成符合生物力学的臀部压力曲面
    :param f_left: 左侧总压力
    :param f_right: 右侧总压力
    :param grid_size: 网格尺寸，默认32x32
    :return: 二维压力数组，单位N，范围0-500N
    """
    # 初始化压力网格（用原生列表代替numpy）
    surface = [[0.0 for _ in range(grid_size)] for _ in range(grid_size)]
    
    # 人体坐骨结节位置（相对坐标）
    # 左侧坐骨: (x=0.35, y=0.6)
    # 右侧坐骨: (x=0.65, y=0.6)
    left_ischial_x = int(0.35 * grid_size)
    right_ischial_x = int(0.65 * grid_size)
    ischial_y = int(0.6 * grid_size)
    
    # 坐骨压力峰值，与总压力成正比
    left_peak = f_left * 0.7  # 70%的压力集中在坐骨
    right_peak = f_right * 0.7
    
    # 高斯分布参数
    sigma = grid_size * 0.08  # 压力扩散范围
    
    # --- 1. 生成坐骨结节核心压力 (后部) ---
    for y in range(grid_size):
        for x in range(grid_size):
            # 左侧坐骨压力
            dx_l = x - left_ischial_x
            dy_l = y - ischial_y
            dist_l = math.sqrt(dx_l*dx_l + dy_l*dy_l)
            p_left = left_peak * math.exp(-(dist_l**2) / (2 * sigma**2))
            
            # 右侧坐骨压力
            dx_r = x - right_ischial_x
            dy_r = y - ischial_y
            dist_r = math.sqrt(dx_r*dx_r + dy_r*dy_r)
            p_right = right_peak * math.exp(-(dist_r**2) / (2 * sigma**2))
            
            surface[y][x] += p_left + p_right
            
    # --- 2. 生成大腿前部压力 (前部，y坐标较小处) ---
    # 大腿接触区通常在坐骨前方，即 y < ischial_y
    # 我们模拟两条从坐骨向前延伸的压力带
    thigh_length = int(0.4 * grid_size)
    thigh_width_sigma = grid_size * 0.06
    
    # 随时间微调大腿压力的重心，模拟轻微挪动
    thigh_shift = random.uniform(-0.05, 0.05) * grid_size
    
    for y in range(ischial_y - thigh_length, ischial_y):
        if y < 0: continue
        
        # 距离坐骨的纵向距离 (0到1)
        progress = (ischial_y - y) / thigh_length
        # 压力随距离衰减
        decay = 1.0 - progress * 0.6
        
        for x in range(grid_size):
            # 左大腿中心线
            dx_l = x - (left_ischial_x + thigh_shift * 0.5)
            # 右大腿中心线
            dx_r = x - (right_ischial_x + thigh_shift * 0.5)
            
            # 横向高斯分布
            thigh_p_l = (left_peak * 0.4 * decay) * math.exp(-(dx_l**2) / (2 * thigh_width_sigma**2))
            thigh_p_r = (right_peak * 0.4 * decay) * math.exp(-(dx_r**2) / (2 * thigh_width_sigma**2))
            
            # 加入随机噪点，让前部压力看起来不那么死板
            noise = random.uniform(0.9, 1.1)
            surface[y][x] += (thigh_p_l + thigh_p_r) * noise

    # --- 3. 边缘平滑与限制 ---
    edge = int(0.05 * grid_size)
    for y in range(edge):
        for x in range(grid_size):
            surface[y][x] = 0.0
    for y in range(grid_size - edge, grid_size):
        for x in range(grid_size):
            surface[y][x] = 0.0
    for y in range(grid_size):
        for x in range(edge):
            surface[y][x] = 0.0
        for x in range(grid_size - edge, grid_size):
            surface[y][x] = 0.0
    
    # 限制压力最大值
    for y in range(grid_size):
        for x in range(grid_size):
            if surface[y][x] > 500:
                surface[y][x] = 500.0
            elif surface[y][x] < 0:
                surface[y][x] = 0.0
    
    return surface


def pressure_to_color(pressure, max_pressure=500):
    """压力值转热力图颜色 (蓝-青-黄-红)"""
    norm = pressure / max_pressure
    if norm < 0.25:
        # 蓝到青
        r = 0
        g = int(norm * 4 * 255)
        b = 255
    elif norm < 0.5:
        # 青到黄
        r = int((norm - 0.25) * 4 * 255)
        g = 255
        b = int(255 - (norm - 0.25) * 4 * 255)
    elif norm < 0.75:
        # 黄到橙
        r = 255
        g = int(255 - (norm - 0.5) * 4 * 128)
        b = 0
    else:
        # 橙到红
        r = 255
        g = int(127 - (norm - 0.75) * 4 * 127)
        b = 0
    return f"#{r:02x}{g:02x}{b:02x}"
