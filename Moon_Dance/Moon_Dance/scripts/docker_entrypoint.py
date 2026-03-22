"""
Docker 容器入口脚本
用于批量生成多个模拟设备的 Excel 全天数据报表
"""
import os
import sys
import time
import threading

# 确保项目根目录在 sys.path 中
sys.path.append(os.getcwd())

# 导入业务逻辑
try:
    from src.core.posture_analyzer import generate_daily_data
    from src.utils.excel_exporter import export_daily_report
    from src.config.settings import BASE_PATH
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

# 配置输出目录到 Docker 卷挂载点
OUTPUT_DIR = "/app/output"

def batch_generate_reports(count=5):
    """
    批量生成指定数量的设备全天数据报表
    :param count: 要生成的份数 (模拟多少个人的数据)
    """
    print(f"Starting batch generation for {count} devices...")
    
    # 临时修改 BASE_PATH 以指向输出目录
    # 注意：这里需要 hack 一下 excel_exporter 的路径逻辑，或者手动指定路径
    
    for i in range(1, count + 1):
        try:
            print(f"[{i}/{count}] Generating data for User_{i:03d}...")
            
            # 生成全天数据
            data_rows = generate_daily_data(device_count=1) # 每个文件只包含一个设备的数据
            
            # 生成文件名
            timestamp = time.strftime("%Y%m%d")
            filename = f"DailyReport_User_{i:03d}_{timestamp}.xls"
            full_path = os.path.join(OUTPUT_DIR, filename)
            
            # 兼容新的 generate_daily_data 返回的数据结构（可能是嵌套 JSON，也可能是旧的列表）
            # 如果是新的 realtime_data 格式，需要适配一下
            # 目前 generate_daily_data 依然返回旧的列表格式，所以暂时不需要大改
            # 但为了稳健，我们打印一下第一行看看
            # print(f"DEBUG: First row: {data_rows[0]}")

            from src.core.posture_analyzer import calculate_daily_score
            
            # 计算全天平均偏差率
            total_ratio = 0.0
            row_count = 0
            for row in data_rows:
                try:
                    # row format: [dev_id, time, f_left, f_right, ratio_str]
                    ratio_str = row[4].replace('%', '')
                    ratio_val = float(ratio_str)
                    total_ratio += ratio_val
                    row_count += 1
                except (ValueError, IndexError):
                    continue
                    
            avg_ratio = total_ratio / row_count if row_count > 0 else 0.0
            daily_score = calculate_daily_score(avg_ratio)
            
            header = ["设备编号", "时间点", "左侧受力(N)", "右侧受力(N)", "偏差率(%)"]
            
            with open(full_path, mode='w', encoding='utf_16', newline='') as f:
                # 写入评分模块 (位于顶部显眼位置)
                f.write(f"今日坐姿评分:\t{daily_score}\n")
                f.write(f"平均偏差率:\t{avg_ratio:.2f}%\n")
                f.write("\n")  # 空一行分隔
                
                f.write('\t'.join(header) + '\n')
                for row in data_rows:
                    f.write('\t'.join(row) + '\n')
            
            print(f"   -> Saved to: {filename}")
            
        except Exception as e:
            print(f"   -> Failed: {e}")

    print("\nBatch generation complete!")
    print(f"Files are located in: {OUTPUT_DIR}")

if __name__ == "__main__":
    # 从环境变量获取生成数量，默认为 5
    try:
        count = int(os.environ.get("BATCH_COUNT", 5))
    except ValueError:
        count = 5
        
    batch_generate_reports(count)
