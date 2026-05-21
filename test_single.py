import os
import json
from whisper_utils import get_enhanced_text
from qwen_client import call_qwen
from trading_engine import TradingEngine

# ================= 模拟交易账户系统 =================
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
        print("="*50)
        print("当前账户信息")
        print(f"可用资金：{self.cash:.2f} 元")
        print("持仓明细：")
        if self.holdings:
            for code, amount in self.holdings.items():
                print(f"  股票代码：{code}，持有股数：{amount}")
        else:
            print("  无持仓")
        print("="*50)

# ================= 主测试流程 =================
if __name__ == "__main__":
    # 1. 初始化账户和交易引擎
    account = TradingAccount(initial_cash=1_000_000)
    engine = TradingEngine(account)

    print("===== 初始账户状态 =====")
    account.show_account_info()

    # 2. 配置
    TEST_AUDIO = "test_audio_1.wav"
    stock_names = ["比亚迪", "贵州茅台", "宁德时代", "招商银行", "中国平安", "科大讯飞"]

    # 3. 语音转文字+生成增强文本
    print("\n===== 开始单条语音测试 =====")
    enhanced_text = get_enhanced_text(TEST_AUDIO, stock_names)
    if not enhanced_text:
        print("增强文本生成失败，测试终止")
        exit()
    print(f"生成的增强文本：{enhanced_text}")

    # 4. 调用大模型解析交易指令
    result = call_qwen(enhanced_text, prompt_style="cot_example")
    if not result:
        print("解析失败，测试终止")
        exit()

    print(f"解析成功，最终交易指令：{json.dumps(result, ensure_ascii=False, indent=2)}")

    # 5. 提取交易参数
    code = result["code"]
    price = float(result["price"])
    amount_str = result["amount"]
    transaction_type = result["transaction_type"]
    order_type = result["order_type"]
    audio_name = os.path.basename(TEST_AUDIO)

    # 处理数量
    if amount_str == "all":
        amount = "all"
    else:
        amount = int(amount_str)

    # 6. 执行交易
    print("\n===== 开始执行交易 =====")
    if order_type in ["market_order", "market"]:
        # 市价单：直接成交
        if transaction_type == "buy":
            account.buy(code, price, amount, audio_name)
        else:
            account.sell(code, price, amount, audio_name)
    else:
        # 限价单（包括 "limit", "limit_order" 等）：挂单后立即触发成交（简化版）
        engine.limit_order(code, price, amount, transaction_type, audio_name)
        engine.update_price(code, price)   # 以当前价格触发，立即成交

    # 7. 打印交易后的账户信息
    print("\n===== 交易完成后的账户状态 =====")
    account.show_account_info()