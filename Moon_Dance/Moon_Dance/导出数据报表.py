import os
import csv
import ast
from datetime import datetime

# 文件路径配置
INPUT_FILE = "data/data_log.txt"
OUTPUT_DIR = "data"

def export_to_csv():
    """将实时日志数据导出为标准 CSV 报表（可直接用 Excel 打开）"""
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 找不到数据文件: {INPUT_FILE}")
        print("请确保客户端已经发送了数据，并且后端 Worker 正常运行。")
        return

    # 生成带时间戳的输出文件名
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(OUTPUT_DIR, f"数据分析报表_{timestamp_str}.csv")
    
    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"🔄 正在读取数据文件并生成报表...")
    
    count = 0
    # 使用 utf-8-sig 编码，确保 Excel 打开时中文不会乱码
    with open(INPUT_FILE, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8-sig', newline='') as f_out:
        
        writer = csv.writer(f_out)
        
        # 写入报表表头
        writer.writerow([
            '记录编号', '设备 ID', '服务器接收时间 (UTC)', '设备端时间戳', 
            '左压力 (N)', '右压力 (N)', '偏移率', '坐姿状态判断'
        ])
        
        # 逐行解析数据并写入
        for line in f_in:
            try:
                # 跳过空行或格式不符的行
                if '\t' not in line:
                    continue
                    
                receive_time, payload_str = line.split('\t', 1)
                
                # 安全地将字符串解析为字典
                payload = ast.literal_eval(payload_str.strip())
                
                # 提取各项核心数据
                device_id = payload.get('device_id', 'N/A')
                device_timestamp = payload.get('timestamp', 'N/A')
                
                sensors = payload.get('sensors', {})
                left_n = sensors.get('left_force_n', 0.0)
                right_n = sensors.get('right_force_n', 0.0)
                
                analysis = payload.get('analysis', {})
                ratio = analysis.get('deviation_ratio', 0.0)
                status = analysis.get('posture_status', 'N/A')
                
                count += 1
                
                # 写入一行数据
                writer.writerow([
                    count, device_id, receive_time, device_timestamp, 
                    f"{left_n:.2f}", f"{right_n:.2f}", f"{ratio:.4f}", status
                ])
                
            except Exception as e:
                # 忽略解析错误的单行脏数据
                continue
    
    print("=" * 60)
    print(f"✅ 报表导出成功！")
    print(f"📊 共成功转换并导出 {count} 条数据。")
    print(f"📂 报表已保存至: {output_file}")
    print("=" * 60)
    print("💡 【下载提示】:")
    print("在 VSCode 左侧的『资源管理器』中，展开 data 文件夹，")
    print(f"找到 {os.path.basename(output_file)} 文件，")
    print("右键点击它，选择『下载(Download)』即可保存到你的电脑上，双击用 Excel 完美打开！")

if __name__ == "__main__":
    export_to_csv()
