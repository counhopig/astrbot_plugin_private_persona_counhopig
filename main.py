"""
AstrBot 私聊人格插件 —— 主入口

参考 astrbot_plugin_self_evolution 的 Persona Sim / Effect / Todo / Consolidation 架构，
模块化设计：models → storage → engine → commands → main
"""

import shutil
from pathlib import Path

from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.provider import ProviderRequest
from astrbot.api.star import Context, Star, register

try:
    from astrbot.api.star import StarTools
except Exception:  # pragma: no cover
    StarTools = None

from .config import PluginConfig
from .storage import PersonaStorage
from .models import InteractionMode, InteractionOutcome
from .engine.prompt_builder import PromptBuilder
from .engine.interaction import judge_outcome
from .engine.effect_engine import EffectEngine
from .engine.todo_engine import TodoEngine
from .engine.reflection_engine import ReflectionEngine
from .engine.profile_builder import ProfileBuilder
from .commands.handlers import CommandHandlers


@register(
    "astrbot_plugin_private_persona_counhopig",
    "Sisyphus",
    "AstrBot 私聊人格插件 —— 人格、情感、Effect、Todo、记忆与日结",
    "2.9.1",
)
class PrivatePersonaPlugin(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)
        self.raw_config = config or {}

        # 数据目录：优先使用 AstrBot 规范的 plugin_data 目录
        self.data_dir = self._resolve_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._migrate_legacy_data_dir()

        # 初始化各层
        self.cfg = PluginConfig(self.raw_config)
        self.storage = PersonaStorage(self.data_dir, cache_max=self.cfg.storage_cache_max)
        self.prompt_builder = PromptBuilder(self.cfg, self.storage)
        self.effect_engine = EffectEngine(self.storage)
        self.todo_engine = TodoEngine(self.storage)
        self.reflection_engine = ReflectionEngine(self.storage, self.cfg)
        self.profile_builder = ProfileBuilder(self.storage, self.cfg)
        self.cmd = CommandHandlers(self.cfg, self.storage)

        # 追踪本插件注册的 cron job ID，用于 terminate 时精确清理
        self._cron_job_ids: list[str] = []

        logger.info(f"[PrivatePersona] 插件已加载，人格: {self.cfg.persona_name}")

    def _resolve_data_dir(self) -> Path:
        if StarTools and hasattr(StarTools, "get_data_dir"):
            try:
                return Path(StarTools.get_data_dir("astrbot_plugin_private_persona_counhopig"))
            except Exception as e:
                logger.warning(f"[PrivatePersona] 获取 plugin_data 目录失败，回退本地目录: {e}")
        return Path(__file__).parent / "plugin_data"

    def _migrate_legacy_data_dir(self):
        legacy_data_dir = Path(__file__).parent / "data"
        if not legacy_data_dir.exists() or legacy_data_dir == self.data_dir:
            return

        moved = 0
        for old_file in legacy_data_dir.glob("*.json"):
            new_file = self.data_dir / old_file.name
            if new_file.exists():
                continue
            try:
                shutil.move(str(old_file), str(new_file))
                moved += 1
            except Exception as e:
                logger.warning(f"[PrivatePersona] 迁移历史数据失败: {old_file.name} -> {e}")

        if moved:
            logger.info(f"[PrivatePersona] 已从旧 data 目录迁移 {moved} 个用户数据文件到 plugin_data")

    def _debug(self, msg: str):
        if self.cfg.debug_log_enabled:
            logger.debug(f"[PrivatePersona] {msg}")

    # ============================================================
    # 插件互联 API（供其他 AstrBot 插件调用）
    # ============================================================

    def get_emotion(self, user_id: str) -> dict:
        """返回用户情感状态字典：energy/mood/social_need/last_update。"""
        return self.storage.get_emotion(user_id).to_dict()

    def get_affinity(self, user_id: str) -> float:
        """返回用户好感度（0~100）。"""
        return self.storage.get_affinity(user_id)

    def get_persona_snapshot(self, user_id: str) -> dict:
        """返回完整人格快照，适用于跨插件联动读取。"""
        return self.storage.get_persona_snapshot(user_id)

    # ============================================================
    # 生命周期
    # ============================================================

    async def initialize(self):
        if self.cfg.reflection_enabled and self.cfg.reflection_periodic_cron:
            try:
                job = await self.context.cron_manager.add_basic_job(
                    name="private_persona_periodic_reflection",
                    cron_expression=self.cfg.reflection_periodic_cron,
                    handler=self._periodic_reflection,
                    description="私聊人格插件：周期性自动反思",
                    persistent=False,
                )
                self._cron_job_ids.append(job.job_id)
                logger.info(f"[PrivatePersona] 周期性反思已注册: {self.cfg.reflection_periodic_cron}")
            except Exception as e:
                logger.warning(f"[PrivatePersona] 注册周期性反思失败: {e}")

        if self.cfg.proactive_nudge_enabled and self.cfg.proactive_nudge_cron:
            try:
                job = await self.context.cron_manager.add_basic_job(
                    name="private_persona_proactive_nudge",
                    cron_expression=self.cfg.proactive_nudge_cron,
                    handler=self._proactive_nudge_job,
                    description="私聊人格插件：寂寞时主动问候",
                    persistent=False,
                )
                self._cron_job_ids.append(job.job_id)
                logger.info(f"[PrivatePersona] 主动问候已注册: {self.cfg.proactive_nudge_cron}")
            except Exception as e:
                logger.warning(f"[PrivatePersona] 注册主动问候失败: {e}")

        if self.cfg.emotion_enabled and self.cfg.emotion_decay_cron:
            try:
                job = await self.context.cron_manager.add_basic_job(
                    name="private_persona_emotion_decay",
                    cron_expression=self.cfg.emotion_decay_cron,
                    handler=self._periodic_emotion_decay,
                    description="私聊人格插件：情感自然衰减",
                    persistent=False,
                )
                self._cron_job_ids.append(job.job_id)
                logger.info(f"[PrivatePersona] 情感衰减已注册: {self.cfg.emotion_decay_cron}")
            except Exception as e:
                logger.warning(f"[PrivatePersona] 注册情感衰减失败: {e}")

        logger.info("[PrivatePersona] 初始化完成")

    async def terminate(self):
        """插件卸载/重载时清理本插件注册的 cron 任务，不波及 AstrBot 其他 cron。"""
        await self._cleanup_my_cron_jobs()
        logger.info("[PrivatePersona] 插件终止，已清理 cron 任务")

    async def _cleanup_my_cron_jobs(self):
        """删除本插件之前注册的 cron 任务（基于 tracked job_id）。"""
        cron_mgr = self.context.cron_manager
        for job_id in self._cron_job_ids:
            try:
                await cron_mgr.delete_job(job_id)
                logger.info(f"[PrivatePersona] 已清理 cron 任务: {job_id}")
            except Exception as e:
                logger.warning(f"[PrivatePersona] 清理 cron 任务失败 {job_id}: {e}")
        self._cron_job_ids.clear()

    @filter.on_plugin_unloaded()
    async def on_plugin_unloaded(self, metadata):
        """插件卸载时的兜底清理（AstrBot reload 流程中 terminate() 会先执行，此处为 double-safe）。"""
        await self._cleanup_my_cron_jobs()
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
            # 持久化 UMO，供主动问候使用
            self.storage.save_umo(user_id, event.unified_msg_origin)

            outcome = judge_outcome(msg_text)

            # auto_trigger 必须在 record_interaction 之前调用，
            # 这样 get_hours_since_last_interaction 读取的是上次交互时间而非本次
            if self.cfg.effect_enabled and self.cfg.effect_auto_trigger:
                self.effect_engine.auto_trigger(user_id, msg_text, outcome)
            if self.cfg.todo_enabled and self.cfg.todo_auto_trigger:
                self.todo_engine.auto_trigger(user_id, msg_text, outcome)

            self.storage.record_interaction(user_id, InteractionMode.PASSIVE, outcome)
            self._debug(f"记录互动: passive / {outcome.value}")

            # 轮数计数，触发反思和画像构建（持久化到用户 JSON，重启后不丢失）
            if self.cfg.reflection_enabled:
                count = self.storage.increment_turn_counter(user_id, "reflection")
                if count >= self.cfg.reflection_trigger_turns:
                    self.storage.reset_turn_counter(user_id, "reflection")
                    await self._run_reflection(user_id)

            if self.cfg.profile_building_enabled:
                count = self.storage.increment_turn_counter(user_id, "profile")
                if count >= self.cfg.profile_building_trigger_turns:
                    self.storage.reset_turn_counter(user_id, "profile")
                    await self._run_profile_building(user_id)

    @staticmethod
    def _extract_text(response) -> str:
        """从 LLMResponse 中提取纯文本。使用框架统一的 completion_text 属性。"""
        return getattr(response, "completion_text", "") or ""

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

        if self.cfg.memory_enabled and self.cfg.emotion_enabled:
            emotion = self.storage.append_history_and_recover_emotion(
                user_id, "bot", text, self.cfg.emotion_recovery_per_reply
            )
            self._debug(f"记录Bot回复并恢复情感: {text[:40]} | {emotion.status_str()}")
        elif self.cfg.memory_enabled:
            self.storage.append_history(user_id, "bot", text)
            self._debug(f"记录Bot回复: {text[:40]}")
        elif self.cfg.emotion_enabled:
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

    @filter.command("persona_set_emotion", alias={"设置情感", "pse"})
    async def cmd_persona_set_emotion(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_set_emotion(event):
            yield r

    @filter.command("persona_remove_effect", alias={"删除心绪", "prfe"})
    async def cmd_persona_remove_effect(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_remove_effect(event):
            yield r

    @filter.command("persona_clear_effects", alias={"清空心绪", "pcfe"})
    async def cmd_persona_clear_effects(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_clear_effects(event):
            yield r

    @filter.command("persona_clear_todos", alias={"清空待办", "pctd"})
    async def cmd_persona_clear_todos(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_clear_todos(event):
            yield r

    @filter.command("persona_set_affinity", alias={"设置好感度", "psaf"})
    async def cmd_persona_set_affinity(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_set_affinity(event):
            yield r

    @filter.command("persona_set_nickname", alias={"设置昵称", "psnn"})
    async def cmd_persona_set_nickname(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_set_nickname(event):
            yield r

    @filter.command("persona_history", alias={"对话历史", "ph"})
    async def cmd_persona_history(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_history(event):
            yield r

    @filter.command("persona_debug", alias={"人格调试", "pdbg"})
    async def cmd_persona_debug(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_debug(event):
            yield r

    @filter.command("persona_set_config", alias={"设置配置", "pscfg"})
    async def cmd_persona_set_config(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_set_config(event):
            yield r

    @filter.command("persona_reflections", alias={"反思记录", "prf"})
    async def cmd_persona_reflections(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_reflections(event):
            yield r

    @filter.command("persona_facts", alias={"画像事实", "pf"})
    async def cmd_persona_facts(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_facts(event):
            yield r

    @filter.command("persona_clear_reflections", alias={"清空反思", "pcr"})
    async def cmd_persona_clear_reflections(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_clear_reflections(event):
            yield r

    @filter.command("persona_remove_fact", alias={"删除事实", "prmf"})
    async def cmd_persona_remove_fact(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_remove_fact(event):
            yield r

    @filter.command("persona_help", alias={"人格帮助", "pgh", "help", "?"})
    async def cmd_persona_help(self, event: AstrMessageEvent):
        async for r in self.cmd.cmd_help(event):
            yield r

    # ============================================================
    # 首次私聊问候（占位，让 LLM 自然处理）
    # ============================================================

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_first_chat_greeting(self, event: AstrMessageEvent):
        """首次私聊：发送一条固定的欢迎消息引导用户发现功能。"""
        if not self.cfg.greeting_on_first_chat:
            return
        if event.get_group_id():
            return
        profile = self.storage.get_profile(event.get_sender_id())
        if profile.chat_count > 0:
            return
        # chat_count 由 on_llm_request 的 touch_profile 统一管理，这里不触碰
        name = self.cfg.persona_name
        yield event.plain_result(
            f"嗨～我是 {name} ✨\n"
            f"第一次见面，先自我介绍一下吧～\n"
            f"发送「/persona_help」或「人格帮助」可以看看我都能做什么哦。"
        )

    # ============================================================
    # 反思与画像构建
    # ============================================================

    async def _run_reflection(self, user_id: str):
        """对指定用户触发一次自动反思"""
        try:
            history = self.storage.get_history(user_id)
            if not history:
                return
            messages = [h.to_dict() for h in history[-self.cfg.reflection_history_turns:]]
            prompt = self.reflection_engine.build_prompt(user_id, messages)

            provider_id = await self.context.get_current_chat_provider_id(user_id)
            response = await self.context.llm_generate(
                chat_provider_id=provider_id,
                prompt=prompt,
                system_prompt="你是一个对话反思助手，请客观分析对话并输出指定格式的 JSON。",
            )
            text = self._extract_text(response)
            self.reflection_engine.parse_result(user_id, text)
            self._debug(f"用户 {user_id} 反思完成")
        except Exception as e:
            logger.warning(f"[PrivatePersona] 反思失败: {e}")

    async def _run_profile_building(self, user_id: str):
        """对指定用户触发一次画像构建"""
        try:
            history = self.storage.get_history(user_id)
            if not history:
                return
            messages = [h.to_dict() for h in history[-self.cfg.reflection_history_turns:]]
            prompt = self.profile_builder.build_prompt(user_id, messages)

            provider_id = await self.context.get_current_chat_provider_id(user_id)
            response = await self.context.llm_generate(
                chat_provider_id=provider_id,
                prompt=prompt,
                system_prompt="你是一个用户画像分析助手，请从对话中提取用户事实并输出指定格式的 JSON。",
            )
            text = self._extract_text(response)
            self.profile_builder.parse_result(user_id, text)
            self._debug(f"用户 {user_id} 画像构建完成")
        except Exception as e:
            logger.warning(f"[PrivatePersona] 画像构建失败: {e}")

    def _periodic_emotion_decay(self):
        """周期性情感衰减的 cron handler"""
        for user_id in self.storage.list_users():
            try:
                self.storage.apply_decay(user_id, self.cfg.emotion_decay_per_hour)
            except Exception as e:
                logger.warning(f"[PrivatePersona] 情感衰减失败 {user_id}: {e}")

    def _periodic_reflection(self):
        """周期性反思的 cron handler（同步包装）"""
        for user_id in self.storage.list_users():
            history = self.storage.get_history(user_id)
            if len(history) >= 2:
                import asyncio
                asyncio.create_task(self._run_reflection(user_id))

    def _proactive_nudge_job(self):
        """主动问候的 cron handler（同步包装）"""
        import asyncio
        asyncio.create_task(self._proactive_nudge())

    async def _proactive_nudge(self):
        """遍历所有用户，当 lonely 时间足够长时主动发送问候消息。

        不依赖已被创建的 lonely effect（effect 只在用户发消息时被动创建），
        而是直接根据上次交互时间计算孤独程度。
        """
        import asyncio
        import time
        from astrbot.core.message.message_event_result import MessageChain

        if self.cfg.rest_enabled and self.cfg.is_sleeping():
            return

        LONELY_THRESHOLD_HOURS = 6  # 与 effect_engine 保持一致
        NUDGE_INTENSITY_THRESHOLD = 60  # 强度 >= 60 才发送问候

        now = time.time()
        for user_id in self.storage.list_users():
            umo = self.storage.get_umo(user_id)
            if not umo:
                continue

            # 直接根据持久化的 interactions 记录计算孤独时长
            hours_since = self.storage.get_hours_since_last_interaction(user_id)
            if hours_since < LONELY_THRESHOLD_HOURS:
                continue

            computed_intensity = min(80.0, hours_since * 5)
            if computed_intensity < NUDGE_INTENSITY_THRESHOLD:
                continue

            try:
                profile = self.storage.get_profile(user_id)
                nickname = profile.nickname or "你"
                emotion = self.storage.get_emotion(user_id)
                emotion_desc = emotion.narrative()

                system_prompt = (
                    f"你是「{self.cfg.persona_name}」。{self.cfg.persona_base_prompt}\n"
                    f"你已经很久没有和{nickname}说话了，现在你的心情是：{emotion_desc}，有些想念TA。\n"
                    f"请主动发送一条简短、自然的消息（1~2句话），表达你的想念或轻微的寂寞感。\n"
                    f"语气要自然，像真人发消息一样，不要过于刻意或煽情。\n"
                    f"只输出消息正文，不要加任何前缀或说明。"
                )
                provider_id = await self.context.get_current_chat_provider_id(umo)
                response = await self.context.llm_generate(
                    chat_provider_id=provider_id,
                    prompt=f"主动联系{nickname}",
                    system_prompt=system_prompt,
                )
                text = self._extract_text(response)
                if not text:
                    continue

                chain = MessageChain().message(text)
                await self.context.send_message(umo, chain)
                logger.info(
                    f"[PrivatePersona] 主动问候 {user_id} ({hours_since:.1f}h): {text[:40]}"
                )

                # 记录一次模拟交互，防止下次 cron 立即再次问候
                self.storage.record_interaction(
                    user_id, InteractionMode.ACTIVE, InteractionOutcome.CONNECTED
                )
                # 清理已有的 lonely effect（如果存在）
                effects = self.storage.get_active_effects(user_id)
                for e in effects:
                    if e.effect_type == "lonely":
                        self.storage.remove_effect(user_id, e.id)
                # 问候后更新情感状态
                emotion.on_interact(self.cfg.emotion_recovery_per_reply)
                self.storage.save_emotion(user_id, emotion)

            except Exception as e:
                logger.warning(f"[PrivatePersona] 主动问候失败 {user_id}: {e}")

            # 避免同时并发大量 LLM 请求
            await asyncio.sleep(1)

    # ============================================================
    # LLM 工具
    # ============================================================

    @filter.llm_tool(name="upsert_cognitive_memory")
    async def tool_upsert_cognitive_memory(self, event: AstrMessageEvent, category: str, content: str, evidence: str = "", confidence: float = 1.0):
        """记录或更新关于用户的认知记忆（画像事实）。当对话中了解到用户的新偏好、身份、习惯时调用。"""
        user_id = event.get_sender_id()
        self.profile_builder.upsert_fact(
            user_id=user_id,
            category=category,
            content=content,
            evidence=evidence,
            confidence=confidence,
        )
        self._debug(f"LLM 工具记录认知记忆: [{category}] {content}")
        return {"status": "ok", "message": f"已记录: [{category}] {content}"}
