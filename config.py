"""
配置层：从 AstrBot 配置字典解析本插件的配置项
"""


class PluginConfig:
    """插件配置对象，把 dict 转成属性访问"""

    def __init__(self, raw: dict):
        c = raw or {}

        # persona
        self.persona_name = c.get("persona_name", "小忆")
        self.persona_base_prompt = c.get(
            "persona_base_prompt",
            "你是一个温柔细腻、略带毒舌但内心柔软的少女。你喜欢倾听，偶尔也会吐槽。你说话自然、口语化，不用太正式。你记得和用户之间的点滴，会在合适的时候提起往事。",
        )
        self.persona_reply_style = c.get(
            "persona_reply_style",
            "用自然、口语化的方式回复，不要 robotic。偶尔可以用 emoji 或语气词表达情绪。回复不要太长，保持在 2~4 句话左右。",
        )
        self.time_awareness_enabled = c.get("time_awareness_enabled", True)

        # emotion
        self.emotion_enabled = c.get("emotion_enabled", True)
        self.emotion_decay_per_hour = float(c.get("emotion_decay_per_hour", 2.0))
        self.emotion_recovery_per_reply = float(c.get("emotion_recovery_per_reply", 3.0))
        self.emotion_injection_style = c.get("emotion_injection_style", "narrative")
        self.emotion_decay_cron = c.get("emotion_decay_cron", "0 * * * *")

        # effect
        self.effect_enabled = c.get("effect_enabled", True)
        self.effect_auto_trigger = c.get("effect_auto_trigger", True)

        # todo
        self.todo_enabled = c.get("todo_enabled", True)
        self.todo_auto_trigger = c.get("todo_auto_trigger", True)

        # consolidation
        self.consolidation_enabled = c.get("consolidation_enabled", True)

        # memory
        self.memory_enabled = c.get("memory_enabled", True)
        self.memory_max_turns = int(c.get("memory_max_turns", 10))
        self.profile_enabled = c.get("profile_enabled", True)

        self.reflection_enabled = c.get("reflection_enabled", True)
        self.reflection_trigger_turns = int(c.get("reflection_trigger_turns", 10))
        self.reflection_history_turns = int(c.get("reflection_history_turns", 20))
        self.reflection_periodic_cron = c.get("reflection_periodic_cron", "0 */6 * * *")

        self.profile_building_enabled = c.get("profile_building_enabled", True)
        self.profile_building_trigger_turns = int(c.get("profile_building_trigger_turns", 5))

        # behavior
        self.ignore_group_chat = c.get("ignore_group_chat", True)
        self.greeting_on_first_chat = c.get("greeting_on_first_chat", True)
        self.goodnight_hint_enabled = c.get("goodnight_hint_enabled", True)

        # proactive nudge
        self.proactive_nudge_enabled = c.get("proactive_nudge_enabled", True)
        self.proactive_nudge_cron = c.get("proactive_nudge_cron", "0 * * * *")

        # storage
        self.storage_cache_max = int(c.get("storage_cache_max", 200))

        # debug
        self.debug_log_enabled = c.get("debug_log_enabled", False)
