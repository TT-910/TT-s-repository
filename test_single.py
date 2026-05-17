from whisper_utils import get_enhanced_text
from qwen_client import call_qwen
import json

# ================= 模拟交易账户系统 =================
class TradingAccount:
    def __init__(self, initial_cash=1_000_000):
        # 初始资金，默认100万，可自行修改
        self.cash = initial_cash
        # 持仓字典：key=股票代码，value=持有股数
        self.holdings = {}

    def buy(self, symbol: str, price: float, amount: int) -> bool:
        """执行买入操作"""
        cost = price * amount
        # 校验余额是否足够
        if self.cash >= cost:
            self.cash -= cost
            self.holdings[symbol] = self.holdings.get(symbol, 0) + amount
            print(f"\n买入成交：{symbol} {amount}股，成交价{price:.2f}元，花费{cost:.2f}元")
            return True
        print(f"\n买入失败：余额不足，需要{cost:.2f}元，当前可用资金{self.cash:.2f}元")
        return False

    def sell(self, symbol: str, price: float, amount: int) -> bool:
        """执行卖出操作"""
        current_hold = self.holdings.get(symbol, 0)
        # 校验持仓是否足够
        if current_hold >= amount:
            revenue = price * amount
            self.cash += revenue
            self.holdings[symbol] = current_hold - amount
            # 持仓为0时清除该股票记录
            if self.holdings[symbol] == 0:
                del self.holdings[symbol]
            print(f"\n卖出成交：{symbol} {amount}股，成交价{price:.2f}元，收入{revenue:.2f}元")
            return True
        print(f"\n卖出失败：持仓不足，当前持有{symbol} {current_hold}股，欲卖出{amount}股")
        return False

    def show_account_info(self):
        """打印当前账户完整信息"""
        print("="*50)
        print("当前账户信息")
        print(f"可用资金：{self.cash:.2f} 元")
        print("持仓明细：")
        if self.holdings:
            for code, amount in self.holdings.items():
                print(f"  股票代码：{code}，持有股数：{amount}")
        else:
            print(f"  无持仓")
        print("="*50)

# ================= 主测试流程 =================
if __name__ == "__main__":
    # 1. 初始化账户：初始100万资金，想改初始金额直接改括号里的数字即可
    account = TradingAccount(initial_cash=1_000_000)
    # 先打印初始账户信息
    print("===== 初始账户状态 =====")
    account.show_account_info()

    # 2. 配置项
    TEST_AUDIO = "test_audio_1.wav"  # 你的测试音频文件
    stock_names = ["比亚迪", "贵州茅台", "宁德时代", "招商银行", "中国平安", "科大讯飞"]

    # 3. 语音转文字+生成增强文本
    print("\n===== 开始单条语音测试 =====")
    enhanced_text = get_enhanced_text(TEST_AUDIO)
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

    # 5. 自动执行交易
    print("\n===== 开始执行交易 =====")
    # 从解析结果中提取交易参数
    code = result["code"]
    price = result["price"]
    amount = result["amount"]
    transaction_type = result["transaction_type"]

    # 根据交易方向执行对应操作
    if transaction_type == "buy":
        account.buy(code, price, amount)
    elif transaction_type == "sell":
        account.sell(code, price, amount)
    else:
        print(f"不支持的交易类型：{transaction_type}")
        exit()

    # 6. 打印交易后的账户信息
    print("\n===== 交易完成后的账户状态 =====")
    account.show_account_info()