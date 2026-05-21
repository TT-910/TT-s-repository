import re

def regex_parse(enhanced_text: str):
    # 提取用户指令部分
    if "用户指令：" in enhanced_text:
        inst = enhanced_text.split("用户指令：")[-1]
    else:
        inst = enhanced_text

    # 1. 方向
    if re.search(r"买", inst):
        direction = "buy"
    elif re.search(r"卖", inst):
        direction = "sell"
    else:
        return None

    # 2. 股票代码（从增强文本开头提取）
    code_match = re.search(r"股票代码：(\d{6})", enhanced_text)
    if not code_match:
        return None
    code = code_match.group(1)

    # 3. 数量
    amount = None
    m = re.search(r"(\d+)\s*股", inst)
    if m:
        amount = int(m.group(1))
    elif re.search(r"全部|全仓|所有|all", inst):
        amount = "all"
    else:
        return None

    # 4. 价格与订单类型
    # 先尝试从指令中提取指定价格（如“134.4元”）
    price_match = re.search(r"(\d+(?:\.\d+)?)\s*[元块]", inst)
    if price_match:
        order_type = "limit_order"
        price = float(price_match.group(1))
    else:
        order_type = "market_order"
        # 从增强文本中取当前市价
        price_match2 = re.search(r"当前市价：([\d.]+)元", enhanced_text)
        if price_match2:
            price = float(price_match2.group(1))
        else:
            return None

    return {
        "code": code,
        "order_type": order_type,
        "price": price,
        "amount": amount,
        "transaction_type": direction
    }