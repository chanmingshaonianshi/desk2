#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
坐姿分析核心算法模块
功能：压力差值计算、坐姿评估、评分生成、模拟数据生成
作用：核心业务逻辑实现，所有坐姿相关的计算都在这里处理
使用原因：算法逻辑与接口、界面分离，便于优化和复用
"""
import random
import time
from src.config.settings import RATIO_NORMAL, RATIO_WARNING


def calculate_ratio(f_left, f_right):
    """计算受力差值占比"""
    f_total = f_left + f_right
    return abs(f_left - f_right) / f_total if f_total != 0 else 0.0


def get_assessment(ratio):
    """坐姿评估逻辑"""
    if ratio <= RATIO_NORMAL:
        return "坐姿端正", "normal"
    elif ratio <= RATIO_WARNING:
        return "轻微歪斜", "orange"
    else:
        return "请注意坐姿", "red_bold"


def generate_force_data():
    """生成随机压力数据"""
    f_left = random.uniform(200, 400)
    f_right = random.uniform(200, 400)
    return f_left, f_right


def generate_daily_data(device_count=10):
    """生成全天模拟数据"""
    hours = list(range(8, 25))
    data_rows = []
    
    for dev_id in range(1, device_count + 1):
        for hour in hours:
            f_left, f_right = generate_force_data()
            ratio = calculate_ratio(f_left, f_right)
            
            row = [
                str(dev_id),
                f"{hour:02d}:00",
                f"{f_left:.2f}",
                f"{f_right:.2f}",
                f"{ratio*100:.2f}%"
            ]
            data_rows.append(row)
    
    return data_rows


def generate_daily_data_for_device(device_id):
    hours = list(range(8, 25))
    data_rows = []
    for hour in hours:
        f_left, f_right = generate_force_data()
        ratio = calculate_ratio(f_left, f_right)
        row = [
            str(device_id),
            f"{hour:02d}:00",
            f"{f_left:.2f}",
            f"{f_right:.2f}",
            f"{ratio*100:.2f}%"
        ]
        data_rows.append(row)
    return data_rows


def calculate_daily_score(average_deviation_percent):
    """
    根据全天平均偏差率计算今日坐姿评分（保留用于 Excel 报表）
    
    评分规则（线性映射）:
    - [0, 5]: 100 -> 90 分
    - (5, 25]: 89 -> 60 分
    - (25, 50]: 59 -> 0 分
    - > 50: 0 分
    
    :param average_deviation_percent: 平均偏差率 (单位: %, e.g., 3.5 代表 3.5%)
    :return: 整数评分 (0-100)
    """
    x = average_deviation_percent
    score = 0
    
    if x < 0:
        x = 0  # 理论上偏差率不应为负，做个保护
        
    if 0 <= x <= 5:
        # [0, 5] -> [100, 90]
        # 斜率 k = (90 - 100) / (5 - 0) = -2
        # y = 100 - 2x
        score = 100 - 2 * x
    elif 5 < x <= 25:
        # (5, 25] -> [89, 60]
        # 斜率 k = (60 - 89) / (25 - 5) = -29 / 20 = -1.45
        # y = 89 + k * (x - 5)
        score = 89 - 1.45 * (x - 5)
    elif 25 < x <= 50:
        # (25, 50] -> [59, 0]
        # 斜率 k = (0 - 59) / (50 - 25) = -59 / 25 = -2.36
        # y = 59 + k * (x - 25)
        score = 59 - 2.36 * (x - 25)
    else:
        # > 50
        score = 0
        
    # 四舍五入取整 (使用 +0.5 确保 .5 向上取整)
    return int(score + 0.5)


def calculate_health_score(good_posture_ratio, sedentary_compliance_ratio):
    """
    综合健康评分算法 (0-100 分)
    
    评分公式：
    健康评分 = 坐姿质量得分(50分) + 久坐提醒合规得分(50分)
    
    维度1 - 坐姿质量得分 (满分 50 分):
        基于实时坐姿评分的全天平均值。
        良好坐姿占比越高，得分越高。
        posture_score = good_posture_ratio * 50
    
    维度2 - 久坐提醒合规得分 (满分 50 分):
        用户是否根据久坐提醒离开座位 ≥ 5 分钟。
        合规次数占总提醒次数的比率越高，得分越高。
        compliance_score = compliance_ratio * 50
        若当天无久坐提醒触发（入座时长短），默认满分。
    
    :param good_posture_ratio: 良好坐姿数据占比 (0~1)
    :param sedentary_compliance_ratio: 久坐提醒合规率 (0~1)，
                                       即 (合规离座次数 / 总提醒次数)，
                                       若无提醒则传 1.0
    :return: (总分int, 各维度明细dict)
    """
    # ---- 维度1: 坐姿质量得分 (满分 50 分) ----
    posture_score = round(good_posture_ratio * 50, 1)
    
    # ---- 维度2: 久坐提醒合规得分 (满分 50 分) ----
    compliance_score = round(sedentary_compliance_ratio * 50, 1)
    
    # 总分
    total = round(posture_score + compliance_score)
    total = max(0, min(100, total))
    
    breakdown = {
        "posture_score": posture_score,
        "compliance_score": compliance_score
    }
    return total, breakdown

