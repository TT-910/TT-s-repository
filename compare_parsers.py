import pandas as pd
import json
from regex_parser import regex_parse
from qwen_client import call_qwen

def normalize_order_type(ot):
    """将 market/limit 统一转换为 market_order/limit_order"""
    if ot in ("market", "market_order"):
        return "market_order"
    if ot in ("limit", "limit_order"):
        return "limit_order"
    return ot

def is_correct(parsed, expected):
    if parsed is None:
        return False
    for key in expected:
        if key not in parsed:
            return False
        if key == "price":
            if abs(parsed[key] - expected[key]) > 0.01:
                return False
        elif key == "order_type":
            if normalize_order_type(parsed[key]) != normalize_order_type(expected[key]):
                return False
        else:
            if parsed[key] != expected[key]:
                return False
    return True

df = pd.read_csv('test_20.csv', encoding='gbk')   # 确保编码正确
df['expected'] = df['expected_json'].apply(json.loads)

regex_ok = 0
llm_ok = 0
total = len(df)

for idx, row in df.iterrows():
    enhanced = row['enhanced_text']
    expected = row['expected']
    
    reg_res = regex_parse(enhanced)
    print(f"===== {row['audio_path']} =====")
    print(f"增强文本: {enhanced[:100]}...")
    print(f"正则解析结果: {reg_res}")
    print(f"期望结果: {expected}")
    
    if is_correct(reg_res, expected):
        regex_ok += 1
    else:
        print("→ 正则匹配失败")
    
    llm_res = call_qwen(enhanced, prompt_style="cot_example")
    if is_correct(llm_res, expected):
        llm_ok += 1
    else:
        print(f"大模型解析结果: {llm_res}")
    print()

print(f"\n正则准确率: {regex_ok}/{total} = {regex_ok/total*100:.1f}%")
print(f"大模型准确率: {llm_ok}/{total} = {llm_ok/total*100:.1f}%")