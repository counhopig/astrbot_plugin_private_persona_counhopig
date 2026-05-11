"""
Effect 引擎：自动根据互动结果和状态触发 Effect
"""

from datetime import datetime

from astrbot.api import logger

from ..models import InteractionOutcome
from ..storage import PersonaStorage


class EffectEngine:
    def __init__(self, storage: PersonaStorage):
        self.storage = storage

    def _has_active_effect(self, user_id: str, effect_type: str) -> bool:
        """检查指定类型的 Effect 是否已存在且活跃，用于去重。"""
        active = self.storage.get_active_effects(user_id)
        return any(e.effect_type == effect_type for e in active)

    def auto_trigger(self, user_id: str, msg_text: str, outcome: InteractionOutcome):
        emotion = self.storage.get_emotion(user_id)

        # 1. 被冷落 / hostile → wronged
        if outcome == InteractionOutcome.MISSED and not self._has_active_effect(user_id, "wronged"):
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
        if outcome == InteractionOutcome.AWKWARD and not self._has_active_effect(user_id, "awkward"):
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
        hours_since = self.storage.get_hours_since_last_interaction(user_id)

        if hours_since > 6 and not self._has_active_effect(user_id, "lonely"):
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
        if (hour >= 23 or hour < 2) and emotion.energy < 40 and not self._has_active_effect(user_id, "tired"):
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
