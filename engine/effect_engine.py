"""
Effect 引擎：自动根据互动结果和状态触发 Effect
"""

import time
from datetime import datetime

from astrbot.api import logger

from ..models import InteractionOutcome
from ..storage import PersonaStorage


class EffectEngine:
    def __init__(self, storage: PersonaStorage):
        self.storage = storage

    def auto_trigger(self, user_id: str, msg_text: str, outcome: InteractionOutcome):
        now = time.time()
        emotion = self.storage.get_emotion(user_id)

        # 1. 被冷落 / hostile → wronged
        if outcome == InteractionOutcome.MISSED:
            self.storage.add_effect(
                user_id,
                effect_type="wronged",
                intensity=60.0,
                source_detail="主动搭话但被冷落，期望落空",
                decay_style="slow",
                recovery_style="social",
                duration_hours=4.0,
            )
            logger.debug(f"[EffectEngine] triggered wronged for {user_id}")

        # 2. 尴尬 → awkward
        if outcome == InteractionOutcome.AWKWARD:
            self.storage.add_effect(
                user_id,
                effect_type="awkward",
                intensity=40.0,
                source_detail="气氛有点僵，不知道说什么好",
                decay_style="fast",
                recovery_style="social",
                duration_hours=2.0,
            )
            logger.debug(f"[EffectEngine] triggered awkward for {user_id}")

        # 3. 长时间未互动 → lonely
        last_interactions = self.storage.get_today_interactions(user_id)
        if last_interactions:
            last_ts = last_interactions[-1].timestamp
            hours_since = (now - last_ts) / 3600
        else:
            profile = self.storage.get_profile(user_id)
            hours_since = (now - profile.last_seen) / 3600

        if hours_since > 6:
            self.storage.add_effect(
                user_id,
                effect_type="lonely",
                intensity=min(80.0, hours_since * 5),
                source_detail=f"已经 {hours_since:.0f} 小时没说话了，有点寂寞",
                decay_style="slow",
                recovery_style="social",
                duration_hours=8.0,
            )
            logger.debug(f"[EffectEngine] triggered lonely ({hours_since:.1f}h) for {user_id}")

        # 4. 深夜低能量 → tired
        hour = datetime.now().hour
        if (hour >= 23 or hour < 2) and emotion.energy < 40:
            self.storage.add_effect(
                user_id,
                effect_type="tired",
                intensity=50.0,
                source_detail="夜深了，有点困",
                decay_style="linear",
                recovery_style="sleep",
                duration_hours=6.0,
            )
            logger.debug(f"[EffectEngine] triggered tired for {user_id}")
