PROMPT_BASIC = """请解析以下交易指令，直接输出JSON格式，不要包含任何其他文字说明。
JSON必须包含以下字段：
- code: 股票代码 (字符串)
- order_type: 订单类型 (market 或 limit)
- price: 价格 (数字，如果是市价单则填当前市价)
- amount: 数量 (整数)
- transaction_type: 交易方向 (buy 或 sell)

解析规则：
1. 如果用户指定了固定价格（如 50元、51块），则 order_type = limit，price = 指定价格
2. 如果用户说“便宜X元”“低X元”，则 order_type = limit，price = 当前市价 - X
3. 如果用户说“贵X元”“高X元”，则 order_type = limit，price = 当前市价 + X
4. 如果没有指定任何价格，order_type = market，price = 当前市价

输入内容：{enhanced_text}
"""

PROMPT_COT = """请逐步思考并解析交易指令，最后输出JSON。
思考步骤：
1. 确定交易方向（买入还是卖出）
2. 确定订单类型（市价还是限价）
   - 有指定价格、便宜X元、贵X元 → 限价单 limit
   - 无价格 → 市价单 market
3. 提取或计算价格
   - 指定价格 → 使用指定价格
   - 便宜X元 → 市价 - X
   - 贵X元 → 市价 + X
   - 无价格 → 使用当前市价
4. 提取数量
5. 整理成JSON输出

输入内容：{enhanced_text}
"""

PROMPT_COT_EXAMPLE = """示例：
输入："股票代码：002594，当前市价：248.50元。用户指令：买入比亚迪一百股"
输出：{{"code": "002594", "order_type": "market", "price": 248.50, "amount": 100, "transaction_type": "buy"}}

示例2：
输入："股票代码：002230，当前市价：53元，用户指定价格：无，价格偏移：-2元。用户指令：比现在价格便宜2块买入科大讯飞100股"
输出：{{"code": "002230", "order_type": "limit", "price": 51, "amount": 100, "transaction_type": "buy"}}

示例3：
输入："股票代码：002594，当前市价：248.5元，用户指定价格：245，价格偏移：0元。用户指令：245块卖出比亚迪200股"
输出：{{"code": "002594", "order_type": "limit", "price": 245.0, "amount": 200, "transaction_type": "sell"}}

现在请解析以下内容：
{enhanced_text}
"""