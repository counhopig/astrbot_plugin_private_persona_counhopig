"""
AstrBot 私聊人格插件 —— 主入口

参考 astrbot_plugin_self_evolution 的 Persona Sim / Effect / Todo / Consolidation 架构，
模块化设计：models → storage → engine → commands → main
"""

from pathlib import Path

from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.provider import ProviderRequest
from astrbot.api.star import Context, Star, register

from .config import PluginConfig
from .storage import PersonaStorage
from .engine.prompt_builder import PromptBuilder
from .engine.interaction import judge_outcome
from .engine.effect_engine import EffectEngine
from .engine.todo_engine import TodoEngine
from .commands.handlers import CommandHandlers


@register(
    "astrbot_plugin_private_persona_counhopig",
    "Sisyphus",
    "AstrBot 私聊人格插件 —— 人格、情感、Effect、Todo、记忆与日结",
    "2.0.0",
)
class PrivatePersonaPlugin(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)
        self.raw_config = config or {}

        # 数据目录
        self.data_dir = Path(__file__).parent / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 初始化各层
        self.cfg = PluginConfig(self.raw_config)
        self.storage = PersonaStorage(self.data_dir)
        self.prompt_builder = PromptBuilder(self.cfg, self.storage)
        self.effect_engine = EffectEngine(self.storage)
        self.todo_engine = TodoEngine(self.storage)
        self.cmd = CommandHandlers(self.cfg, self.storage)

        logger.info(f"[PrivatePersona] 插件已加载，人格: {self.cfg.persona_name}")

    def _debug(self, msg: str):
        if self.cfg.debug_log_enabled:
            logger.debug(f"[PrivatePersona] {msg}")

    # ============================================================
    # 生命周期
    # ============================================================

    async def initialize(self):
        logger.info("[PrivatePersona] 初始化完成")

    @filter.on_plugin_unloaded()
    async def on_plugin_unloaded(self, metadata):
        logger.info("[PrivatePersona] 插件卸载，数据已持久化")

    # ============================================================
    # LLM Prompt 注入
    # ============================================================

    @filter.on_llm_request()
    async def on_llm_request(self, event: AstrMessageEvent, req: ProviderRequest):
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        is_private = not bool(group_id)

        if self.cfg.ignore_group_chat and not is_private:
            return
        if not is_private:
            return

        # 更新画像
        if self.cfg.profile_enabled:
            self.storage.touch_profile(user_id, event.get_sender_name() or "")

        # 情感衰减
        if self.cfg.emotion_enabled:
            self.storage.apply_decay(user_id, self.cfg.emotion_decay_per_hour)

        # 清理过期 effect
        if self.cfg.effect_enabled:
            self.storage.cleanup_expired_effects(user_id)

        # 构建并注入
        injections = self.prompt_builder.build_all(user_id)
        full = "\n\n".join(injections)
        req.system_prompt = (req.system_prompt or "") + "\n\n" + full
        self._debug(f"注入完成，长度={len(full)} 字符")

    # ============================================================
    # 消息监听
    # ============================================================

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message_listener(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        is_private = not bool(group_id)

        if self.cfg.ignore_group_chat and not is_private:
            return

        msg_text = event.message_str or ""
        if not msg_text:
            return

        if self.cfg.memory_enabled:
            self.storage.append_history(user_id, "user", msg_text)
            self._debug(f"记录用户消息: {msg_text[:40]}")

        if is_private:
            from .models import InteractionMode
            outcome = judge_outcome(msg_text)
            self.storage.record_interaction(user_id, InteractionMode.PASSIVE, outcome)
            self._debug(f"记录互动: passive / {outcome.value}")

            if self.cfg.effect_enabled and self.cfg.effect_auto_trigger:
                self.effect_engine.auto_trigger(user_id, msg_text, outcome)
            if self.cfg.todo_enabled and self.cfg.todo_auto_trigger:
                self.todo_engine.auto_trigger(user_id, msg_text, outcome)

    @staticmethod
    def _extract_text(response) -> str:
        """从 LLMResponse / Completion / Message / TextBlock 中提取纯文本"""
        if isinstance(response, str):
            return response
        # AstrBot LLMResponse wrapper
        if hasattr(response, "completion"):
            completion = response.completion
            if isinstance(completion, str):
                return completion
            # Anthropic Message style
            if hasattr(completion, "content"):
                parts = []
                for block in completion.content:
                    if hasattr(block, "text"):
                        parts.append(block.text)
                    elif isinstance(block, str):
                        parts.append(block)
                return " ".join(parts)
            return str(completion)
        # OpenAI style
        if hasattr(response, "choices") and response.choices:
            choice = response.choices[0]
            if hasattr(choice, "message") and hasattr(choice.message, "content"):
                return str(choice.message.content) or ""
        # Fallback
        return str(response)

    @filter.on_llm_response()
    async def on_llm_response(self, event: AstrMessageEvent, response):
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        is_private = not bool(group_id)

        if self.cfg.ignore_group_chat and not is_private:
            return
        if not response:
            return

        text = self._extract_text(response)
        if not text:
            return

        if self.cfg.memory_enabled:
            self.storage.append_history(user_id, "bot", text)
            self._debug(f"记录Bot回复: {text[:40]}")

        if self.cfg.emotion_enabled:
            emotion = self.storage.get_emotion(user_id)
            emotion.on_interact(self.cfg.emotion_recovery_per_reply)
            self.storage.save_emotion(user_id, emotion)
            self._debug(f"互动后情感恢复: {emotion.status_str()}")

    # ============================================================
    # 命令路由
    # ============================================================

    @filter.command("persona", alias={"人格", "pg"})
    async def cmd_persona(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_persona(event):
            yield r

    @filter.command("persona_effects", alias={"心绪", "pfx"})
    async def cmd_persona_effects(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_effects(event):
            yield r

    @filter.command("persona_todo", alias={"待办", "pft"})
    async def cmd_persona_todo(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_todo(event):
            yield r

    @filter.command("persona_today", alias={"今日人格", "ptd"})
    async def cmd_persona_today(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_today(event):
            yield r

    @filter.command("persona_consolidate", alias={"日结", "pcn"})
    async def cmd_persona_consolidate(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_consolidate(event):
            yield r

    @filter.command("persona_apply", alias={"人格影响", "pap"})
    async def cmd_persona_apply(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_apply(event):
            yield r

    @filter.command("persona_add_effect", alias={"添加心绪", "pafe"})
    async def cmd_persona_add_effect(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_add_effect(event):
            yield r

    @filter.command("persona_add_todo", alias={"添加待办", "pat"})
    async def cmd_persona_add_todo(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_add_todo(event):
            yield r

    @filter.command("persona_done_todo", alias={"完成待办", "pdt"})
    async def cmd_persona_done_todo(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_done_todo(event):
            yield r

    @filter.command("persona_reset", alias={"人格重置", "pgr"})
    async def cmd_persona_reset(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_reset(event):
            yield r

    @filter.command("persona_note", alias={"人格备注", "pgn"})
    async def cmd_persona_note(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_note(event):
            yield r

    @filter.command("persona_affinity", alias={"好感度", "pgaf"})
    async def cmd_persona_affinity(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_affinity(event):
            yield r

    @filter.command("persona_help", alias={"人格帮助", "pgh"})
    async def cmd_persona_help(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_help(event):
            yield r

    # ============================================================
    # 首次私聊问候（占位，让 LLM 自然处理）
    # ============================================================

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_first_chat_greeting(self, event: AstrMessageEvent):
        if not self.cfg.greeting_on_first_chat:
            return
        if event.get_group_id():
            return
        profile = self.storage.get_profile(event.get_sender_id())
        if profile.chat_count > 1:
            return
        # 不强制发送，由 Prompt 注入引导 LLM 自然问候
