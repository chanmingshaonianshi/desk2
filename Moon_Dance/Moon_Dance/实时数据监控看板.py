import os
import time
import json
import ast

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_table(data_lines):
    clear_screen()
    print("="*90)
    print(f"{'设备 ID':<15} | {'时间戳':<25} | {'左压力 (N)':<10} | {'右压力 (N)':<10} | {'偏移率':<10}")
    print("-" * 90)
    
    for line in data_lines[-15:]: # 只显示最近15条
        try:
            # 尝试解析格式： 2024-xx-xxTxxZ    {'device_id': ...}
            if '\t' in line:
                timestamp_str, payload_str = line.split('\t', 1)
                payload = ast.literal_eval(payload_str.strip())
                
                device_id = payload.get('device_id', 'N/A')
                # 尝试从 datetime 提取时间，或使用 timestamp
                timestamp = payload.get('timestamp', 'N/A')
                
                sensors = payload.get('sensors', {})
                left_n = sensors.get('left_force_n', 0.0)
                right_n = sensors.get('right_force_n', 0.0)
                
                analysis = payload.get('analysis', {})
                ratio = analysis.get('deviation_ratio', 0.0)
                
                print(f"{device_id:<15} | {timestamp_str:<25} | {left_n:<10.1f} | {right_n:<10.1f} | {ratio:<10.4f}")
        except Exception as e:
            pass
    print("="*90)
    print("正在实时监听云端接收的数据... (按 Ctrl+C 退出)")

def main():
    # 兼容本地和服务器的不同路径
    log_file_paths = [
        "data/data_log.txt",
        "backend/data/data_log.txt",
        "/app/data/data_log.txt"
    ]
    
    target_file = None
    for path in log_file_paths:
        if os.path.exists(path):
            target_file = path
            break
            
    if not target_file:
        print("等待数据写入... (暂未找到 data/data_log.txt 文件)")
        target_file = "data/data_log.txt"
        os.makedirs("data", exist_ok=True)
        open(target_file, 'a').close() # 创建空文件

    print(f"正在监听数据文件: {target_file}")
    
    # 模拟 tail -f
    with open(target_file, "r", encoding="utf-8") as f:
        # 移动到文件末尾的前面一点，或者直接读取全部
        lines = f.readlines()
        if lines:
            print_table(lines)
            
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.5)
                continue
            
            lines.append(line)
            # 保持内存里只有最后20行
            if len(lines) > 20:
                lines = lines[-20:]
            print_table(lines)

if __name__ == "__main__":
    main()