import whisper
import akshare as ak
from rapidfuzz.distance.Levenshtein import normalized_similarity as ratio
import os
import json
from datetime import datetime

STOCK_CACHE_FILE = "stock_list_cache.json"

# 全局股票数据缓存（程序启动时自动加载）
STOCK_CACHE = None
# 兜底映射表（接口异常时使用）
FALLBACK_STOCKS = {
    "宁德时代": "300750",
    "比亚迪": "002594",
    "贵州茅台": "600519",
    "科大讯飞": "002230",
    "招商银行": "600036",
    "中国平安": "601318"
}

# 模型升级为medium
model = whisper.load_model("medium")

# 全量A股股票数据加载与缓存函数 ---
def load_all_stocks():
    global STOCK_CACHE
    if STOCK_CACHE is not None:
        return STOCK_CACHE

    # ---------- 策略1：在线获取（akshare） ----------
    try:
        print("[系统初始化] 尝试从东方财富在线获取全量A股...")
        df = ak.stock_zh_a_spot_em()
        if not df.empty:
            stock_dict = dict(zip(df["名称"].tolist(), df["代码"].tolist()))
            # 写入本地缓存
            cache_data = {
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data": stock_dict
            }
            with open(STOCK_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False)
            print(f"[系统初始化] 在线获取成功，共 {len(stock_dict)} 只股票")
            STOCK_CACHE = stock_dict
            return stock_dict
    except Exception as e:
        print(f"[系统初始化] 在线获取失败：{e}")

    # ---------- 策略2：读取本地缓存 ----------
    if os.path.exists(STOCK_CACHE_FILE):
        try:
            with open(STOCK_CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
            stock_dict = cache.get("data", {})
            if stock_dict:
                print(f"[系统初始化] 使用本地缓存（上次更新：{cache.get('update_time', '未知')}），共 {len(stock_dict)} 只股票")
                STOCK_CACHE = stock_dict
                return stock_dict
        except Exception as e:
            print(f"[系统初始化] 读取缓存失败：{e}")

    # ---------- 策略3：尝试备选 akshare 接口（名称代码表） ----------
    try:
        print("[系统初始化] 尝试从 akshare 股票基本信息接口获取...")
        df = ak.stock_info_a_code_name()   # 这个接口通常较稳定
        if not df.empty:
            stock_dict = dict(zip(df["name"].tolist(), df["code"].tolist()))
            with open(STOCK_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump({"update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                           "data": stock_dict}, f, ensure_ascii=False)
            print(f"[系统初始化] 备选接口成功，共 {len(stock_dict)} 只股票")
            STOCK_CACHE = stock_dict
            return stock_dict
    except Exception as e:
        print(f"[系统初始化] 备选接口也失败：{e}")

    # ---------- 策略4：使用扩充的兜底股票列表 ----------
    print("[系统初始化] 所有在线方式失败，使用扩充的本地兜底股票列表")
    STOCK_CACHE = get_extended_fallback_stocks()
    return STOCK_CACHE

# --- 程序启动时自动加载股票数据 ---
# 这行代码会在导入模块时自动执行，只执行一次
STOCK_CACHE = None
load_all_stocks()

def transcribe_audio(audio_path: str):
    """语音转文字函数（完全保留）"""
    result = model.transcribe(
        audio_path,
        language="zh",
        initial_prompt="这是一段A股股票交易语音指令，包含股票名称、买入、卖出、股数、价格等信息。"
    )
    return result["text"].strip()

def fix_transaction_direction(text: str):
    """买卖方向纠错函数（完全保留）"""
    text = text.replace("买人", "买入").replace("卖人", "卖出")
    text = text.replace("买如", "买入").replace("卖如", "卖出")
    text = text.replace("买出", "卖出").replace("卖进", "买入")
    return text

from rapidfuzz.distance.Levenshtein import normalized_similarity as ratio
from pypinyin import lazy_pinyin

def extract_stock_name(text: str, name_list: list):
    import re
    from pypinyin import lazy_pinyin
    from rapidfuzz.distance.Levenshtein import normalized_similarity as ratio

    # ===================== 步骤1：精确匹配（=====================
    for name in name_list:
        if name in text:
            print(f"[匹配股票] 精确匹配：{name}")
            return name

    # ===================== 步骤2：清洗文本，只保留中文（=====================
    pure_text = re.sub(r'[^\u4e00-\u9fa5]', '', text)  # 删掉数字/符号/英文

    # ===================== 步骤3：2字简称匹配=====================
    short_words = re.findall(r'[\u4e00-\u9fa5]{2}', pure_text)
    if short_words:
        best_short = None
        best_short_score = 0
        for word in short_words:
            for name in name_list:
                score = ratio(word, name)
                if score > best_short_score:
                    best_short_score = score
                    best_short = name
        if best_short_score >= 0.3:
            print(f"[匹配股票] 简称匹配：{best_short}")
            return best_short

    # 步骤4：语音错字模糊匹配=====================
    best_match = None
    best_score = 0.0
    threshold = 0.32  # 稳定容错阈值
    text_pinyin = "".join(lazy_pinyin(pure_text))

    for name in name_list:
        edit_score = ratio(pure_text, name)
        char_match = sum(1 for c in name if c in pure_text) / len(name)
        name_pinyin = "".join(lazy_pinyin(name))
        pinyin_score = ratio(text_pinyin, name_pinyin)

        # 拼音权重最高，适配语音识别错误
        total_score = edit_score * 0.2 + char_match * 0.3 + pinyin_score * 0.5

        if total_score > best_score and total_score > threshold:
            best_score = total_score
            best_match = name

    if best_match:
        print(f"[匹配股票] 模糊纠错匹配：{best_match}（得分：{best_score:.2f}）")
        return best_match

    print("[匹配失败] 未找到对应股票")
    return None


import time

import requests

def get_real_price_sina(code):
    """
    新浪财经免费实时行情
    code: 纯数字代码，如 '600519' 或 '000001'
    自动补全市场前缀（sh/sz）
    """
    # 判断沪市还是深市：沪市6开头，其余深市（包括创业板3开头）
    if code.startswith('6'):
        full_code = f"sh{code}"
    else:
        full_code = f"sz{code}"

    url = f"https://hq.sinajs.cn/list={full_code}"
    headers = {
        "Referer": "https://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        res.encoding = "gbk"
        data = res.text.split(",")
        if len(data) > 3:
            # 不同数据返回格式略有差异，价格字段固定在第4个
            price = float(data[3])
            return price
    except Exception as e:
        print(f"[新浪行情] 获取失败：{e}")
    return None

def get_code_and_price(stock_name: str):
    stock_data = load_all_stocks()
    name_list = list(stock_data.keys())
    
    matched_name = extract_stock_name(stock_name, name_list)
    
    if not matched_name:
        return None, None
    
    code = stock_data[matched_name]
    price = get_real_price_sina(code)
    
    if price is not None:
        return code, round(price, 2)
    else:
        print(f"[接口异常] 实时行情获取失败，使用兜底价格")
        fallback_prices = {
            "300750": 423.00,
            "002594": 96.30,
            "600519": 1332.95,
            "002230": 47.00,
            "600036": 37.65,
            "601318": 55.50
        }
        return code, fallback_prices.get(code, 0.0)

def get_enhanced_text(audio_path: str, stock_names=None):
    """生成增强文本（支持：市价、固定价格、相对价格）"""
    text = transcribe_audio(audio_path)
    print(f"[原始识别] {text}")
    
    text = fix_transaction_direction(text)
    print(f"[方向纠错] {text}")
    
    code, price = get_code_and_price(text)
    if not code:
        return None

    # ================= 支持所有价格指令 =================
    import re
    
    # 1. 查找固定价格（如：51元、51块、51块钱）
    fixed_price = None
    pattern = r"(\d+(\.\d+)?)[块元]"
    match_price = re.search(pattern, text)
    if match_price:
        fixed_price = float(match_price.group(1))

    # 2. 查找相对价格（便宜/低/贵/高）
    offset = 0
    if "便宜" in text or "低" in text:
        num_match = re.search(r"(\d+)", text)
        if num_match:
            offset = -int(num_match.group(1))
    elif "贵" in text or "高" in text:
        num_match = re.search(r"(\d+)", text)
        if num_match:
            offset = int(num_match.group(1))

    # 3. 生成最终增强文本
    enhanced_text = (
        f"股票代码：{code}，当前市价：{price}元，"
        f"用户指定价格：{fixed_price if fixed_price else '无'}，"
        f"价格偏移：{offset}元。"
        f"用户指令：{text}"
    )
    
    print(f"[增强文本] {enhanced_text}")
    return enhanced_text