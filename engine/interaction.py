"""
互动判定：根据用户消息内容推断 InteractionOutcome
"""

from ..models import InteractionOutcome

_FRIENDLY_KEYWORDS = {"哈哈", "谢谢", "爱你", "好的", "嗯嗯", "在的", "在呀", "嗨", "你好", "早安", "晚安", "拜拜", "嘻嘻"}
_HOSTILE_KEYWORDS = {"滚", "走开", "别烦", "闭嘴", "不想", "别吵", "别闹", "不理", "无聊", "没意思", "烦死了"}
_COLD_KEYWORDS = {"哦", "嗯", "好", "知道了", "随便", "无所谓"}


def judge_outcome(msg_text: str) -> InteractionOutcome:
    """根据用户消息简单判定互动 outcome"""
    text = msg_text.lower()
    for kw in _HOSTILE_KEYWORDS:
        if kw in text:
            return InteractionOutcome.MISSED
    for kw in _FRIENDLY_KEYWORDS:
        if kw in text:
            return InteractionOutcome.CONNECTED
    for kw in _COLD_KEYWORDS:
        if kw in text:
            return InteractionOutcome.AWKWARD
    if len(msg_text.strip()) <= 2:
        return InteractionOutcome.AWKWARD
    return InteractionOutcome.CONNECTED
