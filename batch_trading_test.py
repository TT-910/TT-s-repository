import os
import json
from whisper_utils import get_enhanced_text
from qwen_client import call_qwen
from typing import List, Dict

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

    def sell(self, symbol: str, price: float, amount: int, audio_name: str) -> bool:
        current_hold = self.holdings.get(symbol, 0)
        if amount == "all":
            amount = current_hold  # 处理全仓卖出
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
            print(f"  无持仓")
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
def get_audio_files(folder_path: str) -> List[str]:
    """获取文件夹里所有的音频文件，支持wav、mp3、m4a格式"""
    audio_extensions = ('.wav', '.mp3', '.m4a', '.flac')
    audio_files = []
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(audio_extensions):
            audio_files.append(filename)
    # 按文件名排序，保证测试顺序稳定
    audio_files.sort()
    return audio_files

if __name__ == "__main__":
    # ================= 配置区域 =================
    # 1. 测试语音文件夹路径
    AUDIO_FOLDER = "audio_tests"
    # 2. 初始资金，默认100万
    INITIAL_CASH = 1_000_000
    # 3. 支持的股票列表
    stock_names = ["比亚迪", "贵州茅台", "宁德时代", "招商银行", "中国平安", "科大讯飞"]
    # ===========================================

    # 检查文件夹是否存在
    if not os.path.exists(AUDIO_FOLDER):
        print(f"错误：找不到文件夹 '{AUDIO_FOLDER}'，请先创建文件夹并放入测试语音")
        exit()

    # 获取所有测试语音
    audio_files = get_audio_files(AUDIO_FOLDER)
    if not audio_files:
        print(f"错误：文件夹 '{AUDIO_FOLDER}' 里没有找到音频文件")
        exit()

    # 初始化账户
    account = TradingAccount(initial_cash=INITIAL_CASH)
    print("="*60)
    print("开始批量语音交易回测")
    print(f"测试语音文件夹：{AUDIO_FOLDER}")
    print(f"测试语音数量：{len(audio_files)} 条")
    print(f"初始资金：{INITIAL_CASH:.2f} 元")
    print("="*60)

    # 逐条处理测试语音
    for idx, audio_filename in enumerate(audio_files, 1):
        audio_path = os.path.join(AUDIO_FOLDER, audio_filename)
        print(f"\n[{idx}/{len(audio_files)}] 正在处理：{audio_filename}")
        
        # 1. 语音转文字+生成增强文本
        enhanced_text = get_enhanced_text(audio_path, stock_names)
        if not enhanced_text:
            print(f"  跳过：无法生成增强文本")
            account.transaction_history.append({
                "audio": audio_filename,
                "type": "解析",
                "code": "-",
                "price": 0,
                "amount": 0,
                "status": "失败(语音识别/股票匹配失败)"
            })
            continue

        # 2. 调用大模型解析交易指令
        result = call_qwen(enhanced_text, prompt_style="cot_example")
        if not result:
            print(f"  跳过：无法解析交易指令")
            account.transaction_history.append({
                "audio": audio_filename,
                "type": "解析",
                "code": "-",
                "price": 0,
                "amount": 0,
                "status": "失败(API解析失败)"
            })
            continue

        # 3. 提取交易参数并处理特殊情况
        code = result["code"]
        price = float(result["price"])
        
        # 关键修复：处理amount为"all"或数字字符串的情况
        amount_str = result["amount"]
        if amount_str == "all":
            amount = "all"
        else:
            try:
                amount = int(amount_str)
            except ValueError:
                print(f"  跳过：无法解析数量字段 '{amount_str}'")
                account.transaction_history.append({
                    "audio": audio_filename,
                    "type": result["transaction_type"],
                    "code": code,
                    "price": price,
                    "amount": amount_str,
                    "status": "失败(无效数量)"
                })
                continue

        transaction_type = result["transaction_type"]

        print(f"  解析结果：{transaction_type} {code} {amount}股 @ {price:.2f}元")

        if transaction_type == "buy":
            account.buy(code, price, amount, audio_filename)
        elif transaction_type == "sell":
            account.sell(code, price, amount, audio_filename)
        else:
            print(f"  跳过：不支持的交易类型 {transaction_type}")
            account.transaction_history.append({
                "audio": audio_filename,
                "type": transaction_type,
                "code": code,
                "price": price,
                "amount": amount,
                "status": "失败(不支持的交易类型)"
            })

    # 输出最终结果
    account.show_transaction_history()
    account.show_account_info()

    print("\n批量回测完成！")