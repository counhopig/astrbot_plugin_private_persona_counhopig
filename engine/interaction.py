"""
互动判定：根据用户消息内容推断 InteractionOutcome
"""

from ..models import InteractionOutcome

_FRIENDLY_KEYWORDS = {"哈哈", "谢谢", "爱你", "好的", "嗯嗯", "在的", "在呀", "嗨", "你好", "早安", "晚安", "拜拜", "嘻嘻"}
_HOSTILE_KEYWORDS = {"滚", "走开", "别烦", "闭嘴", "不想", "别吵", "别闹", "不理", "无聊", "没意思", "烦死了"}
# 去掉 "好"：单字"好"在日常中多为正面/中性，误判率高
# 改为精确匹配：只在消息完全等于该词时才视为冷淡
_COLD_EXACT = {"哦", "嗯", "好", "知道了", "随便", "无所谓"}


def judge_outcome(msg_text: str) -> InteractionOutcome:
    """根据用户消息简单判定互动 outcome"""
    text = msg_text.lower()
    for kw in _HOSTILE_KEYWORDS:
        if kw in text:
            return InteractionOutcome.MISSED
    for kw in _FRIENDLY_KEYWORDS:
        if kw in text:
            return InteractionOutcome.CONNECTED
    stripped = msg_text.strip()
    # 精确匹配冷淡词，或消息极短（≤2字符）时判为 AWKWARD
    if stripped in _COLD_EXACT or len(stripped) <= 2:
        return InteractionOutcome.AWKWARD
    return InteractionOutcome.CONNECTED
