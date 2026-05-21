import os
import csv
import json
import re
from whisper_utils import get_enhanced_text
from qwen_client import call_qwen

AUDIO_FOLDER = "audio_tests"
STOCK_NAMES = ["比亚迪", "贵州茅台", "宁德时代", "招商银行", "中国平安", "科大讯飞"]

# 按数字顺序排序
def extract_number(f):
    match = re.search(r'\d+', f)
    return int(match.group()) if match else 0

audio_files = [f for f in os.listdir(AUDIO_FOLDER) if f.endswith('.wav')]
audio_files.sort(key=extract_number)
selected = audio_files[:20]   # 取前20条

rows = []
for audio in selected:
    audio_path = os.path.join(AUDIO_FOLDER, audio)
    enhanced = get_enhanced_text(audio_path, STOCK_NAMES)
    if not enhanced:
        print(f"跳过 {audio}: 增强文本生成失败")
        continue
    result = call_qwen(enhanced, prompt_style="cot_example")
    expected_json = json.dumps(result, ensure_ascii=False) if result else ""
    rows.append([audio, enhanced, expected_json])

with open('test_20.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f)
    writer.writerow(['audio_path', 'enhanced_text', 'expected_json'])
    writer.writerows(rows)

print(f"已生成 test_20.csv，共 {len(rows)} 条。请用 Excel 核对 expected_json 列。")