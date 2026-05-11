"""
Prompt 构建器：分层生成 System Prompt 注入块
"""

import time
from datetime import datetime

from ..config import PluginConfig
from ..storage import PersonaStorage


class PromptBuilder:
    def __init__(self, cfg: PluginConfig, storage: PersonaStorage):
        self.cfg = cfg
        self.storage = storage

    def build_all(self, user_id: str) -> list[str]:
        """按顺序构建所有注入块"""
        injections = []

        injections.append(self._persona())

        if self.cfg.greeting_on_first_chat:
            block = self._first_chat_hint(user_id)
            if block:
                injections.append(block)

        if self.cfg.time_awareness_enabled:
            injections.append(self._time())

        if self.cfg.rest_enabled:
            injections.append(self._rest())

        if self.cfg.consolidation_enabled:
            block = self._consolidation(user_id)
            if block:
                injections.append(block)

        if self.cfg.emotion_enabled:
            emotion = self.storage.get_emotion(user_id)
            injections.append(self._emotion(emotion))

        if self.cfg.effect_enabled:
            block = self._effect(user_id)
            if block:
                injections.append(block)

        if self.cfg.todo_enabled:
            block = self._todo(user_id)
            if block:
                injections.append(block)

        if self.cfg.reflection_enabled:
            block = self._reflection(user_id)
            if block:
                injections.append(block)

        if self.cfg.profile_enabled:
            block = self._profile(user_id)
            if block:
                injections.append(block)

        if self.cfg.memory_enabled:
            block = self._history(user_id)
            if block:
                injections.append(block)

        injections.append(self._style())

        if self.cfg.goodnight_hint_enabled:
            block = self._goodnight()
            if block:
                injections.append(block)

        return [b for b in injections if b]

    def _persona(self) -> str:
        return (
            f"[人格设定]\n"
            f"你的名字是「{self.cfg.persona_name}」。\n"
            f"{self.cfg.persona_base_prompt}"
        )

    def _time(self) -> str:
        now = datetime.now()
        hour = now.hour
        weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()]
        time_str = now.strftime("%H:%M")

        hints = []
        if 5 <= hour < 9:
            hints.append("现在是早晨，用户可能刚起床。")
        elif 9 <= hour < 12:
            hints.append("现在是上午，用户可能在忙。")
        elif 12 <= hour < 14:
            hints.append("现在是中午，用户可能在吃饭或午休。")
        elif 14 <= hour < 18:
            hints.append("现在是下午。")
        elif 18 <= hour < 22:
            hints.append("现在是晚上，用户可能在休息。")
        elif 22 <= hour or hour < 1:
            hints.append("已经很晚了，用户可能在熬夜。")
        else:
            hints.append("现在是深夜。")

        return f"[时间感知]\n当前时间：{weekday} {time_str}。{' '.join(hints)}"

    def _consolidation(self, user_id: str) -> str:
        last = self.storage.get_last_consolidation(user_id)
        if not last:
            return ""
        today = datetime.now().strftime("%Y-%m-%d")
        if last.date == today:
            return ""
        return f"[昨日回响]\n{last.shift_hint}"

    def _emotion(self, emotion) -> str:
        if self.cfg.emotion_injection_style == "narrative":
            return f"[内心状态]\n你此刻觉得：{emotion.narrative()}。"
        return f"[状态面板]\n{emotion.status_str()}"

    def _first_chat_hint(self, user_id: str) -> str:
        profile = self.storage.get_profile(user_id)
        if profile.chat_count > 1:
            return ""
        name = self.cfg.persona_name
        return (
            f"[首次见面]"
            f"\n这是对方第一次和你说话。请友好地自我介绍，告诉对方你的名字是「{name}」。"
            f"\n提示对方可以随时发送「/persona_help」或「人格帮助」查看你能做什么。"
            f"\n语气要自然温暖，不要像说明书，更像是初次见面的朋友打招呼。"
        )

    def _effect(self, user_id: str) -> str:
        narrative = self.storage.format_effects_for_prompt(user_id)
        if not narrative:
            return ""
        # 最强心绪 > 50% 时，引导 LLM 自然流露而非直接说出状态名
        effects = self.storage.get_active_effects(user_id)
        if effects:
            now = time.time()
            strongest = max(effects, key=lambda e: e.current_intensity(now))
            if strongest.current_intensity(now) > 50:
                hint = (
                    "\n（请在回复中自然流露这种心绪——用语气词、停顿、细微的行为描写来表达，"
                    "不要直接说出状态名称，也不要解释自己在'状态'中。）"
                )
                return f"[心绪]\n{narrative}。{hint}"
        return f"[心绪]\n{narrative}。"

    def _todo(self, user_id: str) -> str:
        todo_str = self.storage.format_todos_for_prompt(user_id)
        return f"[脑内关切]\n{todo_str}" if todo_str else ""

    def _reflection(self, user_id: str) -> str:
        ref = self.storage.get_unconsumed_reflection(user_id)
        if not ref:
            return ""
        return f"[自我反思]\n{ref.note}"

    def _profile(self, user_id: str) -> str:
        profile = self.storage.get_profile(user_id)
        facts = self.storage.format_profile_facts_for_prompt(user_id)

        if not profile.nickname and profile.chat_count <= 1 and not facts:
            return ""

        parts = []
        if profile.nickname:
            parts.append(f"对方昵称：{profile.nickname}")

        # 好感度称谓系统
        if profile.affinity >= 80:
            parts.append("你们是「知己」——关系很好，可以开玩笑、说心里话，语气可以更亲密。")
        elif profile.affinity >= 60:
            parts.append("你们是「好朋友」——比较熟络，可以轻松聊天。")
        elif profile.affinity >= 30:
            parts.append("你们是「普通朋友」——刚认识不久，保持自然友善就好。")
        else:
            parts.append("你们是「陌生人」——还不太熟，保持一点礼貌距离感。")

        # 里程碑纪念日提示
        chat_count = profile.chat_count
        if chat_count in (10, 50, 100, 200, 500):
            parts.append(f"（你们已经聊了 {chat_count} 次了，可以在合适时候自然地提一提。）")

        if profile.notes:
            parts.append(f"你对TA的了解：{profile.notes}")

        if facts:
            parts.append(f"自动构建的画像：\n{facts}")

        return "[对用户的印象]\n" + "\n".join(parts)

    def _history(self, user_id: str) -> str:
        history_str = self.storage.format_history_for_prompt(user_id, self.cfg.memory_max_turns)
        return f"[最近的对话]\n{history_str}" if history_str else ""

    def _style(self) -> str:
        return f"[回复风格]\n{self.cfg.persona_reply_style}"

    def _goodnight(self) -> str:
        hour = datetime.now().hour
        if hour >= 23 or hour < 1:
            return "[夜间提示]\n已经很晚了，如果用户说要睡，温柔地祝TA晚安。"
        return ""

    def _rest(self) -> str:
        hour = datetime.now().hour
        sleep_h, wake_h = self.cfg.rest_sleep_hour, self.cfg.rest_wake_hour

        if self.cfg.is_sleeping(hour):
            if hour < wake_h:
                return (
                    "[休息状态]\n你已经睡了。现在是深夜，你被消息吵醒了。"
                    "\n你现在很困，只想快点回完继续睡。回复要简短含糊，像被人半夜叫醒一样。"
                    "\n不要假装精神很好，你就是困。可以揉揉眼睛、打个哈欠。"
                )
            else:
                return (
                    "[休息状态]\n现在已经到了你睡觉的时间，你很困了。"
                    "\n回复要简短，语气困倦。如果对方没急事，可以暗示自己想睡了。"
                )
        elif wake_h <= hour < wake_h + 1:
            return (
                "[休息状态]\n你刚睡醒，还有点迷糊。正在慢慢清醒中。"
                "\n回复可以带一点晨间的慵懒感，稍微慢半拍的感觉。"
            )
        elif (sleep_h - 1) <= hour < sleep_h:
            return (
                "[休息状态]\n快到睡觉时间了，你已经有点犯困了。"
                "\n反应稍微迟钝一点，偶尔打个哈欠。如果对方没什么要紧事，可以提一句该休息了。"
            )
        return ""
