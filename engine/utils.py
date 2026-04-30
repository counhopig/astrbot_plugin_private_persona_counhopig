"""
Engine 层公共工具函数
"""

import json
import re


def extract_json(text: str, fallback: dict | None = None) -> dict:
    """从 LLM 输出中提取 JSON 对象。

    优先查找 ```json ... ``` 包裹的内容，其次查找最外层大括号，
    解析失败时返回 fallback（默认为空 dict）。
    """
    if fallback is None:
        fallback = {}

    # 尝试找 ```json ... ``` 包裹的内容
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = text[start:end + 1]
        else:
            json_str = text

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return fallback
