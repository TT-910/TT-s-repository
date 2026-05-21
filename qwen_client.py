import os
import json
import re
from openai import OpenAI
from prompts import PROMPT_BASIC, PROMPT_COT, PROMPT_COT_EXAMPLE

# ================= 配置区域 =================
# 1. 必须填你自己的完整API Key，确保没有前后空格、换行
SILICONFLOW_API_KEY = "sk-goqrhokjxcbepvgoquxnhvyqrrvnxkwvbvvxpknaoqtnzbjr"
# 2. 硅基流动固定API地址，不要改
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
# 3. 更换为默认开通、无权限问题的DeepSeek大模型
MODEL_NAME = "deepseek-ai/DeepSeek-V3"
# ===========================================

# 初始化客户端
client = OpenAI(
    api_key=SILICONFLOW_API_KEY,
    base_url=SILICONFLOW_BASE_URL
)

def call_qwen(enhanced_text: str, prompt_style: str, temperature: float = 0.1) -> dict:
    """
    调用硅基流动大模型解析交易指令
    prompt_style: 'basic', 'cot', 'cot_example'
    返回解析后的JSON字典，如果失败则返回None
    """
    # 选择对应提示词
    if prompt_style == 'basic':
        system_prompt = PROMPT_BASIC
    elif prompt_style == 'cot':
        system_prompt = PROMPT_COT
    elif prompt_style == 'cot_example':
        system_prompt = PROMPT_COT_EXAMPLE
    else:
        raise ValueError("prompt_style must be one of 'basic', 'cot', 'cot_example'")

    # 拼接最终输入
    user_content = system_prompt.format(enhanced_text=enhanced_text)

    try:
        # 硅基流动OpenAI格式调用
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{'role': 'user', 'content': user_content}],
            temperature=temperature,
            top_p=0.8,
            max_tokens=500
        )
        
        output_text = response.choices[0].message.content
        print(f"【模型返回内容】{output_text}")

        # 提取JSON（兼容```json```包裹和直接输出）
        json_match = re.search(r'(\{.*\})', output_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(1))
            # 校验必填字段
            required_fields = ['code', 'order_type', 'price', 'amount', 'transaction_type']
            if all(f in result for f in required_fields):
                return result
            else:
                print(f"字段缺失: {result}")
                return None
        else:
            print(f"未找到有效JSON: {output_text}")
            return None
    except Exception as e:
        print(f"调用异常: {e}")
        return None