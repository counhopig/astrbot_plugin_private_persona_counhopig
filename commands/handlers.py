"""
命令处理器：所有用户命令的响应逻辑
"""

import time

from astrbot.api.event import AstrMessageEvent

from ..config import PluginConfig
from ..models import TodoType, InteractionMode, InteractionOutcome
from ..storage import PersonaStorage


class CommandHandlers:
    def __init__(self, cfg: PluginConfig, storage: PersonaStorage):
        self.cfg = cfg
        self.storage = storage

    # ---------- 状态查看 ----------

    async def cmd_persona(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        is_private = not bool(group_id)
        name = self.cfg.persona_name

        lines = [f"=== {name} 的人格状态 ==="]

        if self.cfg.emotion_enabled:
            emotion = self.storage.get_emotion(user_id)
            lines.append(f"\n[内心状态]")
            lines.append(emotion.status_str())
            lines.append(f"感觉：{emotion.narrative()}")

        if self.cfg.effect_enabled:
            effects = self.storage.get_active_effects(user_id)
            lines.append(f"\n[心绪] {len(effects)} 个活跃")
            for e in effects:
                lines.append(f"  · {e.effect_type} ({e.current_intensity(time.time()):.0f}%) — {e.source_detail}")

        if self.cfg.todo_enabled:
            todos = self.storage.get_active_todos(user_id)
            lines.append(f"\n[脑内关切] {len(todos)} 个")
            for t in todos:
                prefix = "【生理】" if t.todo_type == TodoType.INTERNAL.value else "【关系】"
                lines.append(f"  · {prefix} {t.content}")

        if self.cfg.profile_enabled:
            profile = self.storage.get_profile(user_id)
            lines.append(f"\n[对用户的印象]")
            lines.append(f"昵称：{profile.nickname or '未知'}")
            lines.append(f"聊天次数：{profile.chat_count}")
            lines.append(f"好感度：{profile.affinity:.0f}/100")
            if profile.notes:
                lines.append(f"备注：{profile.notes}")

        if self.cfg.memory_enabled:
            history = self.storage.get_history(user_id)
            lines.append(f"\n[记忆]")
            lines.append(f"已记录 {len(history)} 条对话")

        if self.cfg.consolidation_enabled:
            last = self.storage.get_last_consolidation(user_id)
            if last:
                lines.append(f"\n[昨日回响]")
                lines.append(f"{last.shift_hint} ({last.date})")

        lines.append(f"\n场景：{'私聊' if is_private else '群聊'}")
        if not is_private and self.cfg.ignore_group_chat:
            lines.append("(当前群聊中人格系统未激活)")

        yield event.plain_result("\n".join(lines))

    async def cmd_effects(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        effects = self.storage.get_active_effects(user_id)
        if not effects:
            yield event.plain_result("当前没有活跃的心绪 ✨")
            return

        lines = ["=== 活跃心绪 ==="]
        now = time.time()
        for e in effects:
            intensity = e.current_intensity(now)
            remaining_h = (e.expires_at - now) / 3600
            lines.append(
                f"\n[{e.id}] {e.effect_type}"
                f"\n  强度: {intensity:.0f}% (原始 {e.intensity:.0f}%)"
                f"\n  来源: {e.source_detail}"
                f"\n  衰减: {e.decay_style} | 恢复: {e.recovery_style}"
                f"\n  剩余: {remaining_h:.1f}h"
            )
        yield event.plain_result("\n".join(lines))

    async def cmd_todo(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        todos = self.storage.get_active_todos(user_id)
        if not todos:
            yield event.plain_result("当前没有脑内关切 🧠")
            return

        lines = ["=== 脑内关切 ==="]
        for t in todos:
            prefix = "【生理】" if t.todo_type == TodoType.INTERNAL.value else "【关系】"
            lines.append(f"\n[{t.id}] {prefix} {t.content}")
            if t.priority > 0:
                lines.append(f"  优先级: {t.priority}")
        yield event.plain_result("\n".join(lines))

    async def cmd_today(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        interactions = self.storage.get_today_interactions(user_id)

        connected = sum(1 for i in interactions if i.outcome == InteractionOutcome.CONNECTED.value)
        missed = sum(1 for i in interactions if i.outcome == InteractionOutcome.MISSED.value)
        active = sum(1 for i in interactions if i.mode == InteractionMode.ACTIVE.value)
        passive = sum(1 for i in interactions if i.mode == InteractionMode.PASSIVE.value)
        awkward = sum(1 for i in interactions if i.outcome == InteractionOutcome.AWKWARD.value)
        relief = sum(1 for i in interactions if i.outcome == InteractionOutcome.RELIEF.value)

        lines = ["=== 今日互动摘要 ==="]
        lines.append(f"总互动: {len(interactions)}")
        lines.append(f"  主动: {active} | 被动: {passive}")
        lines.append(f"  成功: {connected} | 错过: {missed} | 尴尬: {awkward} | 化解: {relief}")

        if missed >= connected and missed > 0:
            lines.append("\n[轨迹预判] 有落差 📉")
        elif connected > missed and connected >= 2:
            lines.append("\n[轨迹预判] 向上 📈")
        elif awkward > relief:
            lines.append("\n[轨迹预判] 尴尬 😅")
        elif len(interactions) == 0:
            lines.append("\n[轨迹预判] 独处 🍃")
        else:
            lines.append("\n[轨迹预判] 平稳 🌿")

        yield event.plain_result("\n".join(lines))

    # ---------- 日结 ----------

    async def cmd_consolidate(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        cons = self.storage.run_consolidation(user_id)

        emoji_map = {
            "upward": "📈", "gap": "📉", "alone": "🍃",
            "flat": "🌿", "steady": "🌊",
        }
        emoji = emoji_map.get(cons.trajectory, "")

        lines = [
            f"=== 人格日结 {cons.date} {emoji} ===",
            f"\n互动统计:",
            f"  成功: {cons.connected_count} | 错过: {cons.missed_count}",
            f"  主动: {cons.active_count} | 被动: {cons.passive_count}",
            f"  尴尬: {cons.awkward_count} | 化解: {cons.relief_count}",
            f"\n轨迹: {cons.trajectory}",
            f"回响: {cons.shift_hint}",
        ]
        yield event.plain_result("\n".join(lines))

    # ---------- 管理 ----------

    async def cmd_apply(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        msg = event.message_str.strip()
        parts = msg.split(maxsplit=1)

        if len(parts) < 2:
            yield event.plain_result(
                "用法: /persona_apply <bad|awkward|normal|good|relief>\n"
                "例如: /persona_apply bad  — 模拟一次负面互动"
            )
            return

        quality = parts[1].strip().lower()
        outcome_map = {
            "bad": InteractionOutcome.MISSED,
            "awkward": InteractionOutcome.AWKWARD,
            "normal": InteractionOutcome.CONNECTED,
            "good": InteractionOutcome.CONNECTED,
            "relief": InteractionOutcome.RELIEF,
        }
        outcome = outcome_map.get(quality)
        if not outcome:
            yield event.plain_result("无效的影响类型。可选: bad, awkward, normal, good, relief")
            return

        self.storage.record_interaction(user_id, InteractionMode.PASSIVE, outcome)

        if quality == "bad":
            self.storage.add_effect(user_id, "wronged", 60.0, "手动模拟的负面互动", "slow", "social", 4.0)
        elif quality == "awkward":
            self.storage.add_effect(user_id, "awkward", 40.0, "手动模拟的尴尬互动", "fast", "social", 2.0)

        yield event.plain_result(f"已应用互动影响: {quality} ({outcome.value})")

    async def cmd_add_effect(self, event: AstrMessageEvent):
        if not event.is_admin():
            yield event.plain_result("只有管理员可以手动添加心绪哦~")
            return

        user_id = event.get_sender_id()
        msg = event.message_str.strip()
        parts = msg.split(maxsplit=2)

        if len(parts) < 3:
            yield event.plain_result(
                "用法: /persona_add_effect <类型> <来源描述>\n"
                "例如: /persona_add_effect excited 收到了礼物"
            )
            return

        effect_type = parts[1].strip()
        source = parts[2].strip()
        effect = self.storage.add_effect(
            user_id, effect_type, 70.0, source, "slow", "social", 6.0
        )
        yield event.plain_result(f"已添加心绪 [{effect.id}] {effect_type}: {source}")

    async def cmd_add_todo(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        msg = event.message_str.strip()
        parts = msg.split(maxsplit=2)

        if len(parts) < 3:
            yield event.plain_result(
                "用法: /persona_add_todo <need|social> <内容>\n"
                "例如: /persona_add_todo social 想问问TA今天过得怎么样"
            )
            return

        type_str = parts[1].strip().lower()
        content = parts[2].strip()
        todo_type = TodoType.SOCIAL if type_str == "social" else TodoType.INTERNAL
        todo = self.storage.add_todo(user_id, todo_type, content, priority=1)
        prefix = "【生理】" if todo_type == TodoType.INTERNAL else "【关系】"
        yield event.plain_result(f"已添加脑内关切 [{todo.id}] {prefix} {content}")

    async def cmd_done_todo(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        msg = event.message_str.strip()
        parts = msg.split(maxsplit=1)

        if len(parts) < 2:
            yield event.plain_result("用法: /persona_done_todo <待办ID>")
            return

        todo_id = parts[1].strip()
        if self.storage.mark_todo_done(user_id, todo_id):
            yield event.plain_result(f"已标记待办 [{todo_id}] 为完成 ✓")
        else:
            yield event.plain_result(f"未找到待办 [{todo_id}]")

    async def cmd_reset(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        self.storage.reset_user(user_id)
        yield event.plain_result(f"已重置你和 {self.cfg.persona_name} 的所有记忆和状态。仿佛初次见面 ✨")

    async def cmd_note(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        msg = event.message_str.strip()
        parts = msg.split(maxsplit=1)
        profile = self.storage.get_profile(user_id)

        if len(parts) < 2:
            if profile.notes:
                yield event.plain_result(f"当前备注：{profile.notes}")
            else:
                yield event.plain_result("还没有备注。用法：/persona_note 用户喜欢喝奶茶")
            return

        profile.notes = parts[1].strip()
        self.storage.save_profile(user_id, profile)
        yield event.plain_result(f"已记录备注：{profile.notes}")

    async def cmd_affinity(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        msg = event.message_str.strip()
        parts = msg.split(maxsplit=1)
        profile = self.storage.get_profile(user_id)

        if len(parts) < 2:
            desc = ""
            if profile.affinity >= 80:
                desc = "关系很好 💕"
            elif profile.affinity >= 60:
                desc = "比较熟络 😊"
            elif profile.affinity >= 30:
                desc = "刚认识不久 🙂"
            else:
                desc = "还不太熟 😶"
            yield event.plain_result(f"当前好感度：{profile.affinity:.0f}/100 {desc}")
            return

        if not event.is_admin():
            yield event.plain_result("只有管理员可以调整好感度哦~")
            return

        try:
            delta = float(parts[1].strip())
            profile.affinity = max(0.0, min(100.0, profile.affinity + delta))
            self.storage.save_profile(user_id, profile)
            yield event.plain_result(f"好感度已调整为 {profile.affinity:.0f}/100")
        except ValueError:
            yield event.plain_result("用法：/persona_affinity +10 或 /persona_affinity -5")

    # ---------- 手动修改工具 ----------

    async def cmd_set_emotion(self, event: AstrMessageEvent):
        """
        手动设置情感状态
        用法: /persona_set_emotion <energy> <mood> <social_need>
        """
        user_id = event.get_sender_id()
        msg = event.message_str.strip()
        parts = msg.split()

        if len(parts) < 4:
            yield event.plain_result(
                "用法: /persona_set_emotion <活力> <心情> <社交需求>\n"
                "例如: /persona_set_emotion 80 70 50\n"
                "范围: 0~100"
            )
            return

        try:
            energy = max(0.0, min(100.0, float(parts[1])))
            mood = max(0.0, min(100.0, float(parts[2])))
            social = max(0.0, min(100.0, float(parts[3])))
        except ValueError:
            yield event.plain_result("参数必须是数字。用法: /persona_set_emotion 80 70 50")
            return

        emotion = self.storage.get_emotion(user_id)
        emotion.energy = energy
        emotion.mood = mood
        emotion.social_need = social
        emotion.last_update = time.time()
        self.storage.save_emotion(user_id, emotion)
        yield event.plain_result(
            f"情感状态已手动设置:\n"
            f"  活力: {energy:.0f}/100\n"
            f"  心情: {mood:.0f}/100\n"
            f"  社交需求: {social:.0f}/100"
        )

    async def cmd_remove_effect(self, event: AstrMessageEvent):
        """
        删除指定 Effect
        用法: /persona_remove_effect <ID>
        """
        user_id = event.get_sender_id()
        msg = event.message_str.strip()
        parts = msg.split(maxsplit=1)

        if len(parts) < 2:
            yield event.plain_result("用法: /persona_remove_effect <Effect ID>")
            return

        effect_id = parts[1].strip()
        if self.storage.remove_effect(user_id, effect_id):
            yield event.plain_result(f"已删除心绪 [{effect_id}]")
        else:
            yield event.plain_result(f"未找到心绪 [{effect_id}]")

    async def cmd_clear_effects(self, event: AstrMessageEvent):
        """清空所有活跃 Effect"""
        user_id = event.get_sender_id()
        effects = self.storage.get_active_effects(user_id)
        count = 0
        for e in effects:
            if self.storage.remove_effect(user_id, e.id):
                count += 1
        yield event.plain_result(f"已清空 {count} 个活跃心绪 ✨")

    async def cmd_clear_todos(self, event: AstrMessageEvent):
        """清空所有 Todo"""
        user_id = event.get_sender_id()
        todos = self.storage.get_active_todos(user_id)
        count = 0
        for t in todos:
            if self.storage.mark_todo_done(user_id, t.id):
                count += 1
        yield event.plain_result(f"已清空 {count} 个脑内关切 🧹")

    async def cmd_set_affinity(self, event: AstrMessageEvent):
        """
        直接设置好感度（绝对值）
        用法: /persona_set_affinity <0~100>
        """
        user_id = event.get_sender_id()
        msg = event.message_str.strip()
        parts = msg.split(maxsplit=1)

        if len(parts) < 2:
            yield event.plain_result("用法: /persona_set_affinity <0~100>")
            return

        try:
            value = max(0.0, min(100.0, float(parts[1].strip())))
        except ValueError:
            yield event.plain_result("好感度必须是 0~100 之间的数字")
            return

        profile = self.storage.get_profile(user_id)
        profile.affinity = value
        self.storage.save_profile(user_id, profile)
        yield event.plain_result(f"好感度已直接设置为 {value:.0f}/100")

    async def cmd_set_nickname(self, event: AstrMessageEvent):
        """
        设置用户昵称
        用法: /persona_set_nickname <昵称>
        """
        user_id = event.get_sender_id()
        msg = event.message_str.strip()
        parts = msg.split(maxsplit=1)

        if len(parts) < 2:
            yield event.plain_result("用法: /persona_set_nickname <昵称>")
            return

        nickname = parts[1].strip()
        profile = self.storage.get_profile(user_id)
        old = profile.nickname or "未设置"
        profile.nickname = nickname
        self.storage.save_profile(user_id, profile)
        yield event.plain_result(f"昵称已更新: {old} → {nickname}")

    async def cmd_history(self, event: AstrMessageEvent):
        """查看最近对话历史"""
        user_id = event.get_sender_id()
        history = self.storage.get_history(user_id)
        if not history:
            yield event.plain_result("还没有对话记录")
            return

        lines = [f"=== 最近 {len(history)} 条对话 ==="]
        for turn in history[-20:]:
            role = "用户" if turn.role == "user" else "Bot"
            ts = time.strftime("%m-%d %H:%M", time.localtime(turn.timestamp))
            lines.append(f"\n[{ts}] {role}:\n{turn.content}")
        yield event.plain_result("\n".join(lines))

    async def cmd_debug(self, event: AstrMessageEvent):
        """查看原始数据（管理员）"""
        if not event.is_admin():
            yield event.plain_result("只有管理员可以查看调试数据")
            return

        user_id = event.get_sender_id()
        data = self.storage._load(user_id)
        import json
        pretty = json.dumps(data, ensure_ascii=False, indent=2)
        if len(pretty) > 3000:
            pretty = pretty[:3000] + "\n... (已截断)"
        yield event.plain_result(f"=== 原始数据 ===\n```json\n{pretty}\n```")

    async def cmd_set_config(self, event: AstrMessageEvent):
        """
        动态修改配置项（管理员，重启后失效）
        用法: /persona_set_config <key> <value>
        可修改项: persona_name, emotion_enabled, effect_enabled, todo_enabled, memory_enabled
        """
        if not event.is_admin():
            yield event.plain_result("只有管理员可以修改配置")
            return

        user_id = event.get_sender_id()
        msg = event.message_str.strip()
        parts = msg.split(maxsplit=2)

        if len(parts) < 3:
            yield event.plain_result(
                "用法: /persona_set_config <key> <value>\n"
                "可修改项:\n"
                "  persona_name — Bot 名称\n"
                "  emotion_enabled — true/false\n"
                "  effect_enabled — true/false\n"
                "  todo_enabled — true/false\n"
                "  memory_enabled — true/false\n"
                "  consolidation_enabled — true/false"
            )
            return

        key = parts[1].strip()
        value = parts[2].strip()
        bool_keys = {
            "emotion_enabled", "effect_enabled", "todo_enabled",
            "memory_enabled", "profile_enabled", "consolidation_enabled",
            "time_awareness_enabled", "goodnight_hint_enabled",
            "greeting_on_first_chat", "ignore_group_chat",
            "effect_auto_trigger", "todo_auto_trigger",
            "debug_log_enabled",
        }

        if key in bool_keys:
            parsed = value.lower() in ("true", "1", "yes", "on")
            setattr(self.cfg, key, parsed)
            yield event.plain_result(f"配置项 {key} = {parsed}")
        elif key == "persona_name":
            self.cfg.persona_name = value
            yield event.plain_result(f"Bot 名称已改为: {value}")
        elif key in ("emotion_decay_per_hour", "emotion_recovery_per_reply"):
            try:
                setattr(self.cfg, key, float(value))
                yield event.plain_result(f"配置项 {key} = {value}")
            except ValueError:
                yield event.plain_result(f"{key} 必须是数字")
        elif key == "memory_max_turns":
            try:
                setattr(self.cfg, key, int(value))
                yield event.plain_result(f"配置项 {key} = {value}")
            except ValueError:
                yield event.plain_result(f"{key} 必须是整数")
        else:
            yield event.plain_result(f"未知配置项: {key}")

    async def cmd_help(self, event: AstrMessageEvent):
        name = self.cfg.persona_name
        help_text = (
            f"=== {name} · 私聊人格插件 ===\n\n"
            "[状态查看]\n"
            "  /persona          — 查看完整人格状态\n"
            "  /persona_effects  — 查看活跃心绪\n"
            "  /persona_todo     — 查看脑内待办\n"
            "  /persona_today    — 查看今日互动摘要\n"
            "  /persona_history  — 查看最近对话历史\n\n"
            "[日结]\n"
            "  /persona_consolidate — 手动执行人格日结\n\n"
            "[手动修改]\n"
            "  /persona_set_emotion <e> <m> <s>  — 设置情感状态\n"
            "  /persona_set_affinity <0~100>     — 直接设置好感度\n"
            "  /persona_set_nickname <昵称>      — 设置昵称\n"
            "  /persona_set_config <key> <value> — 动态改配置(管理员)\n"
            "  /persona_remove_effect <ID>       — 删除指定心绪\n"
            "  /persona_clear_effects            — 清空所有心绪\n"
            "  /persona_clear_todos              — 清空所有待办\n"
            "  /persona_add_effect <类型> <描述> — 添加心绪\n"
            "  /persona_add_todo <need|social> <内容>\n"
            "  /persona_done_todo <ID>           — 完成待办\n"
            "  /persona_apply <bad|awkward|normal|good|relief>\n"
            "  /persona_reset    — 重置所有记忆\n"
            "  /persona_note     — 添加/查看备注\n"
            "  /persona_affinity — 查看/调整好感度\n"
            "  /persona_debug    — 查看原始数据(管理员)\n\n"
            "[功能]\n"
            "  · 人格注入 + 情感系统 + Effect + Todo + 记忆 + 日结\n\n"
            "[配置]\n"
            "  AstrBot 后台 → 插件配置 → 私聊人格"
        )
        yield event.plain_result(help_text)
