import re
import os
import json
from whisper_utils import get_enhanced_text
from qwen_client import call_qwen
from trading_engine import TradingEngine
from typing import List

# ================= 模拟交易账户系统（与 test_single.py 保持一致） =================
class TradingAccount:
    def __init__(self, initial_cash=1_000_000):
        self.cash = initial_cash
        self.holdings = {}
        self.transaction_history = []

    def buy(self, symbol: str, price: float, amount: int, audio_name: str) -> bool:
        cost = price * amount
        if self.cash >= cost:
            self.cash -= cost
            self.holdings[symbol] = self.holdings.get(symbol, 0) + amount
            self.transaction_history.append({
                "audio": audio_name,
                "type": "买入",
                "code": symbol,
                "price": price,
                "amount": amount,
                "status": "成功"
            })
            return True
        self.transaction_history.append({
            "audio": audio_name,
            "type": "买入",
            "code": symbol,
            "price": price,
            "amount": amount,
            "status": "失败(余额不足)"
        })
        return False

    def sell(self, symbol: str, price: float, amount, audio_name: str) -> bool:
        current_hold = self.holdings.get(symbol, 0)
        if amount == "all":
            amount = current_hold
        if current_hold >= amount:
            revenue = price * amount
            self.cash += revenue
            self.holdings[symbol] = current_hold - amount
            if self.holdings[symbol] == 0:
                del self.holdings[symbol]
            self.transaction_history.append({
                "audio": audio_name,
                "type": "卖出",
                "code": symbol,
                "price": price,
                "amount": amount,
                "status": "成功"
            })
            return True
        self.transaction_history.append({
            "audio": audio_name,
            "type": "卖出",
            "code": symbol,
            "price": price,
            "amount": amount,
            "status": "失败(持仓不足)"
        })
        return False

    def show_account_info(self):
        print("\n" + "="*60)
        print("最终账户状态")
        print(f"可用资金：{self.cash:.2f} 元")
        print("持仓明细：")
        if self.holdings:
            for code, amount in self.holdings.items():
                print(f"  股票代码：{code}，持有股数：{amount}")
        else:
            print("  无持仓")
        print("="*60)

    def show_transaction_history(self):
        print("\n" + "="*60)
        print("批量测试交易明细")
        print("-"*60)
        print(f"{'语音文件':<20} {'类型':<6} {'代码':<10} {'价格':<10} {'数量':<8} {'状态':<15}")
        print("-"*60)
        for tx in self.transaction_history:
            print(f"{tx['audio']:<20} {tx['type']:<6} {tx['code']:<10} {tx['price']:<10.2f} {tx['amount']:<8} {tx['status']:<15}")
        print("="*60)

# ================= 批量测试主流程 =================

def get_audio_files(folder_path: str):
    audio_extensions = ('.wav', '.mp3', '.m4a', '.flac')
    audio_files = []
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(audio_extensions):
            audio_files.append(filename)
    
    # 提取文件名中的数字，按数值排序
    def extract_number(filename):
        match = re.search(r'(\d+)', filename)
        return int(match.group(1)) if match else 0
    
    audio_files.sort(key=extract_number)
    return audio_files

if __name__ == "__main__":
    # 配置
    AUDIO_FOLDER = "audio_tests"          # 语音文件夹
    INITIAL_CASH = 1_000_000
    stock_names = ["比亚迪", "贵州茅台", "宁德时代", "招商银行", "中国平安", "科大讯飞"]

    # 检查文件夹
    if not os.path.exists(AUDIO_FOLDER):
        print(f"错误：找不到文件夹 '{AUDIO_FOLDER}'")
        exit()

    audio_files = get_audio_files(AUDIO_FOLDER)
    if not audio_files:
        print(f"错误：文件夹 '{AUDIO_FOLDER}' 中没有音频文件")
        exit()

    # 初始化账户和交易引擎（只初始化一次，实现记忆）
    account = TradingAccount(initial_cash=INITIAL_CASH)
    engine = TradingEngine(account)

    print("="*60)
    print("开始批量语音交易回测（支持限价单挂单与自动撮合）")
    print(f"测试语音数量：{len(audio_files)} 条")
    print(f"初始资金：{INITIAL_CASH:.2f} 元")
    print("="*60)

    # 逐条处理
    for idx, audio_filename in enumerate(audio_files, 1):
        audio_path = os.path.join(AUDIO_FOLDER, audio_filename)
        print(f"\n[{idx}/{len(audio_files)}] 正在处理：{audio_filename}")

        # 1. 语音识别 + 增强文本
        enhanced_text = get_enhanced_text(audio_path, stock_names)
        if not enhanced_text:
            print("  跳过：无法生成增强文本")
            account.transaction_history.append({
                "audio": audio_filename,
                "type": "解析",
                "code": "-",
                "price": 0,
                "amount": 0,
                "status": "失败(语音识别/股票匹配失败)"
            })
            continue

        # 2. 大模型解析
        result = call_qwen(enhanced_text, prompt_style="cot_example")
        if not result:
            print("  跳过：解析失败")
            account.transaction_history.append({
                "audio": audio_filename,
                "type": "解析",
                "code": "-",
                "price": 0,
                "amount": 0,
                "status": "失败(API解析失败)"
            })
            continue

        # 3. 提取参数
        code = result["code"]
        price = float(result["price"])
        amount_str = result["amount"]
        transaction_type = result["transaction_type"]
        order_type = result.get("order_type", "market_order")   # 兼容旧数据
        audio_short_name = os.path.basename(audio_filename)

        # 处理数量
        if amount_str == "all":
            amount = "all"
        else:
            try:
                amount = int(amount_str)
            except:
                print("  跳过：无效数量")
                continue

        print(f"  解析结果：{transaction_type} {code} {amount}股 @ {price}元, 类型={order_type}")

        # 4. 执行交易（市价单直接成交，限价单挂单）
        if order_type in ["market_order", "market"]:
            if transaction_type == "buy":
                account.buy(code, price, amount, audio_short_name)
            else:
                account.sell(code, price, amount, audio_short_name)
        else:   # 限价单
            engine.limit_order(code, price, amount, transaction_type, audio_short_name)

        # 5. 关键：每次指令后，模拟行情更新，检查所有挂单是否满足成交条件
        #    这里使用当前指令中的价格作为“最新价格”来触发撮合（实际中应从行情接口获取）
        #    注意：如果限价单价格与当前价格相等，买单和卖单都会立即成交；若不等，则继续挂起。
        
        # 可选：打印当前挂单数量
        print(f"  当前挂单数量：{len(engine.order_book)}")

    # 所有指令处理完后，输出结果
    account.show_transaction_history()
    account.show_account_info()

    # 如果有未成交的限价单，打印出来
    if engine.order_book:
        print("\n【警告】以下限价单未成交，仍挂在订单簿中：")
        for order in engine.order_book:
            print(f"  {order.direction} {order.symbol} {order.amount}股 @ {order.price}元")

# 所有指令处理完毕后，模拟一次收盘行情，尝试撮合所有挂单
print("\n===== 模拟收盘行情，检查限价单成交 =====")
# 收集所有挂单中出现的股票代码
stock_codes = set(order.symbol for order in engine.order_book)
for code in stock_codes:
    # 获取该股票的实时价格（可以重用 whisper_utils 中的函数）
    from whisper_utils import get_real_price_sina
    current_price = get_real_price_sina(code)
    if current_price:
        engine.update_price(code, current_price)
        print(f"股票 {code} 最新价 {current_price}，已检查限价单")
    else:
        print(f"无法获取 {code} 实时价，跳过撮合")

# 输出最终挂单情况
if engine.order_book:
    print(f"\n仍有 {len(engine.order_book)} 个限价单未成交：")
    for order in engine.order_book:
        print(f"  {order.direction} {order.symbol} {order.amount}股 @ {order.price}")
else:
    print("所有限价单均已成交")