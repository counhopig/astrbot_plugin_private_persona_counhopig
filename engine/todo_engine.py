"""
Todo 引擎：根据状态和 Effect 自动触发 Todo
"""

from astrbot.api import logger

from ..models import TodoType, InteractionOutcome
from ..storage import PersonaStorage


class TodoEngine:
    def __init__(self, storage: PersonaStorage):
        self.storage = storage

    def auto_trigger(self, user_id: str, msg_text: str, outcome: InteractionOutcome):
        emotion = self.storage.get_emotion(user_id)
        active_effects = self.storage.get_active_effects(user_id)
        effect_types = {e.effect_type for e in active_effects}
        active_todos = self.storage.get_active_todos(user_id)
        todo_contents = {t.content for t in active_todos}

        # 1. tired + 低能量 → need_todo
        if "tired" in effect_types and emotion.energy < 30:
            if "想休息一下" not in todo_contents:
                self.storage.add_todo(user_id, TodoType.INTERNAL, "想休息一下", priority=2)
                logger.debug(f"[TodoEngine] triggered need_todo '想休息一下' for {user_id}")

        # 2. wronged + missed → social_todo
        if "wronged" in effect_types and outcome == InteractionOutcome.MISSED:
            if "想把当时没说完的话接上" not in todo_contents:
                self.storage.add_todo(user_id, TodoType.SOCIAL, "想把当时没说完的话接上", priority=3)
                logger.debug(f"[TodoEngine] triggered social_todo '接上话题' for {user_id}")

        # 3. lonely + 高社交需求 → social_todo
        if "lonely" in effect_types and emotion.social_need > 60:
            if "想找人聊聊天" not in todo_contents:
                self.storage.add_todo(user_id, TodoType.SOCIAL, "想找人聊聊天", priority=2)
                logger.debug(f"[TodoEngine] triggered social_todo '想聊天' for {user_id}")
