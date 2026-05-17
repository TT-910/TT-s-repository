PROMPT_BASIC = """请解析以下交易指令，直接输出JSON格式，不要包含任何其他文字说明。
JSON必须包含以下字段：
- code: 股票代码 (字符串)
- order_type: 订单类型 (market 或 limit)
- price: 价格 (数字，如果是市价单则填当前市价)
- amount: 数量 (整数)
- transaction_type: 交易方向 (buy 或 sell)

输入内容：{enhanced_text}"""

PROMPT_COT = """请逐步思考并解析交易指令，最后输出JSON。
思考步骤：
1. 确定交易方向（买入还是卖出）
2. 确定订单类型（市价还是限价）
3. 提取或使用给定的价格
4. 提取数量
5. 整理成JSON输出

输入内容：{enhanced_text}"""

PROMPT_COT_EXAMPLE = """示例：
输入："股票代码：002594，当前市价：248.50元。用户指令：买入比亚迪一百股"
输出：{{"code": "002594", "order_type": "market", "price": 248.50, "amount": 100, "transaction_type": "buy"}}

现在请解析以下内容：
{enhanced_text}"""