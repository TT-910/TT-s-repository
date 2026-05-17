import os
import json
import pandas as pd
import logging
from typing import Dict, List
from whisper_utils import get_enhanced_text
from qwen_client import call_qwen

# --- 交易引擎部分 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingAccount:
    def __init__(self, initial_cash=1_000_000):
        self.cash = initial_cash
        self.holdings: Dict[str, int] = {}

    def buy(self, symbol: str, price: float, amount: int) -> bool:
        cost = price * amount
        if self.cash >= cost:
            self.cash -= cost
            self.holdings[symbol] = self.holdings.get(symbol, 0) + amount
            logger.info(f"买入 {symbol} {amount}股 @ {price:.2f}, 花费 {cost:.2f}, 剩余现金 {self.cash:.2f}")
            return True
        logger.warning(f"余额不足: 需要 {cost:.2f}, 可用 {self.cash:.2f}")
        return False

    def sell(self, symbol: str, price: float, amount: int) -> bool:
        current = self.holdings.get(symbol, 0)
        if current >= amount:
            revenue = price * amount
            self.cash += revenue
            self.holdings[symbol] = current - amount
            if self.holdings[symbol] == 0:
                del self.holdings[symbol]
            logger.info(f"卖出 {symbol} {amount}股 @ {price:.2f}, 收入 {revenue:.2f}, 剩余现金 {self.cash:.2f}")
            return True
        logger.warning(f"持仓不足: 持有 {current}, 欲卖 {amount}")
        return False

# --- 测试评估部分 ---
def load_test_manifest(manifest_path="test_manifest.csv"):
    df = pd.read_csv(manifest_path)
    df["expected"] = df["expected_json"].apply(json.loads)
    return df

def evaluate(enhanced_text, expected, prompt_style):
    output = call_qwen(enhanced_text, prompt_style)
    if output is None:
        return False, None
    correct = True
    for key in expected:
        if key not in output:
            correct = False
            break
        if key == "price":
            if abs(output[key] - expected[key]) > 0.01:
                correct = False
                break
        else:
            if output[key] != expected[key]:
                correct = False
                break
    return correct, output

def batch_test(manifest_path="test_manifest.csv", stock_names=None):
    df = load_test_manifest(manifest_path)
    results = []
    for idx, row in df.iterrows():
        audio_path = row["audio_path"]
        expected = row["expected"]
        # 已经修改好的行，去掉了csv_path参数，适配实时价格方案
        enhanced = get_enhanced_text(audio_path, stock_names)
        if enhanced is None:
            print(f"跳过 {audio_path}: 增强文本生成失败")
            continue
        for style in ["basic", "cot", "cot_example"]:
            correct, output = evaluate(enhanced, expected, style)
            results.append({
                "case_id": idx,
                "audio": audio_path,
                "prompt_style": style,
                "correct": correct,
                "output": json.dumps(output, ensure_ascii=False) if output else None
            })
    result_df = pd.DataFrame(results)
    result_df.to_csv("batch_results.csv", index=False, encoding="utf-8")
    stats = result_df.groupby("prompt_style")["correct"].agg(["mean", "count"])
    stats["accuracy"] = (stats["mean"] * 100).round(1)
    stats.to_csv("accuracy_stats.csv")
    print("统计完成，结果保存在 accuracy_stats.csv")
    return stats

if __name__ == "__main__":
    # 你指定的6只股票名称
    stock_names = ["比亚迪", "贵州茅台", "宁德时代", "招商银行", "中国平安", "科大讯飞"]
    # 执行批量测试（去掉csv_path参数，适配新的实时函数）
    batch_test("test_manifest.csv", stock_names)