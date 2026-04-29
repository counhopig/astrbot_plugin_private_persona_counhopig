"""
存储引擎层：轻量级 JSON 文件存储
每个用户一个 JSON 文件，内存在线缓存。
"""

import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from astrbot.api import logger

from .models import (
    EmotionState,
    UserProfile,
    ChatTurn,
    Effect,
    Todo,
    InteractionEvent,
    Consolidation,
    TodoType,
    InteractionMode,
    InteractionOutcome,
)


class PersonaStorage:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, dict] = {}

    def _file_path(self, user_id: str) -> Path:
        safe_id = "".join(c for c in user_id if c.isalnum() or c in "-_")
        return self.data_dir / f"{safe_id}.json"

    def _load(self, user_id: str) -> dict:
        if user_id in self._cache:
            return self._cache[user_id]
        path = self._file_path(user_id)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._cache[user_id] = data
                return data
            except Exception as e:
                logger.warning(f"[PersonaStorage] 加载 {user_id} 数据失败: {e}")
        return {}

    def _save(self, user_id: str, data: dict):
        path = self._file_path(user_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._cache[user_id] = data
        except Exception as e:
            logger.warning(f"[PersonaStorage] 保存 {user_id} 数据失败: {e}")

    # ---------- Emotion ----------

    def get_emotion(self, user_id: str) -> EmotionState:
        data = self._load(user_id)
        emotion_data = data.get("emotion")
        if emotion_data:
            return EmotionState.from_dict(emotion_data)
        return EmotionState()

    def save_emotion(self, user_id: str, emotion: EmotionState):
        data = self._load(user_id)
        data["emotion"] = emotion.to_dict()
        self._save(user_id, data)

    def apply_decay(self, user_id: str, decay_per_hour: float) -> EmotionState:
        emotion = self.get_emotion(user_id)
        now = time.time()
        hours_passed = (now - emotion.last_update) / 3600.0
        if hours_passed > 0:
            emotion.decay(decay_per_hour * hours_passed)
            self.save_emotion(user_id, emotion)
        return emotion

    # ---------- Profile ----------

    def get_profile(self, user_id: str) -> UserProfile:
        data = self._load(user_id)
        profile_data = data.get("profile")
        if profile_data:
            return UserProfile.from_dict(profile_data)
        return UserProfile(user_id=user_id)

    def save_profile(self, user_id: str, profile: UserProfile):
        data = self._load(user_id)
        data["profile"] = profile.to_dict()
        self._save(user_id, data)

    def touch_profile(self, user_id: str, nickname: str = "") -> UserProfile:
        profile = self.get_profile(user_id)
        profile.last_seen = time.time()
        if nickname and not profile.nickname:
            profile.nickname = nickname
        profile.chat_count += 1
        self.save_profile(user_id, profile)
        return profile

    # ---------- Memory ----------

    def get_history(self, user_id: str) -> List[ChatTurn]:
        data = self._load(user_id)
        history_data = data.get("history", [])
        return [ChatTurn.from_dict(h) for h in history_data]

    def append_history(self, user_id: str, role: str, content: str):
        data = self._load(user_id)
        history = data.get("history", [])
        history.append(ChatTurn(role=role, content=content).to_dict())
        if len(history) > 100:
            history = history[-100:]
        data["history"] = history
        self._save(user_id, data)

    def format_history_for_prompt(self, user_id: str, max_turns: int) -> str:
        history = self.get_history(user_id)
        turns = history[-(max_turns * 2):]
        if not turns:
            return ""
        lines = []
        for turn in turns:
            role_label = "用户" if turn.role == "user" else "你"
            lines.append(f"{role_label}: {turn.content}")
        return "\n".join(lines)

    # ---------- Effect ----------

    def get_effects(self, user_id: str) -> List[Effect]:
        data = self._load(user_id)
        effects_data = data.get("effects", [])
        return [Effect.from_dict(e) for e in effects_data]

    def add_effect(
        self,
        user_id: str,
        effect_type: str,
        intensity: float,
        source_detail: str,
        decay_style: str = "linear",
        recovery_style: str = "social",
        duration_hours: float = 6.0,
    ) -> Effect:
        now = time.time()
        effect = Effect(
            id=str(uuid.uuid4())[:8],
            effect_type=effect_type,
            intensity=intensity,
            source_detail=source_detail,
            decay_style=decay_style,
            recovery_style=recovery_style,
            created_at=now,
            expires_at=now + duration_hours * 3600,
        )
        data = self._load(user_id)
        effects = data.get("effects", [])
        effects.append(effect.to_dict())
        data["effects"] = effects
        self._save(user_id, data)
        return effect

    def cleanup_expired_effects(self, user_id: str) -> int:
        now = time.time()
        data = self._load(user_id)
        effects = data.get("effects", [])
        before = len(effects)
        effects = [e for e in effects if e.get("expires_at", 0) > now]
        data["effects"] = effects
        self._save(user_id, data)
        return before - len(effects)

    def get_active_effects(self, user_id: str) -> List[Effect]:
        now = time.time()
        effects = self.get_effects(user_id)
        return [e for e in effects if e.expires_at > now and e.current_intensity(now) > 5]

    def format_effects_for_prompt(self, user_id: str) -> str:
        now = time.time()
        effects = self.get_active_effects(user_id)
        narratives = [e.narrative(now) for e in effects if e.narrative(now)]
        return "，".join(narratives) if narratives else ""

    def remove_effect(self, user_id: str, effect_id: str) -> bool:
        data = self._load(user_id)
        effects = data.get("effects", [])
        before = len(effects)
        effects = [e for e in effects if e.get("id") != effect_id]
        data["effects"] = effects
        self._save(user_id, data)
        return len(effects) < before

    # ---------- Todo ----------

    def get_todos(self, user_id: str) -> List[Todo]:
        data = self._load(user_id)
        todos_data = data.get("todos", [])
        return [Todo.from_dict(t) for t in todos_data]

    def add_todo(self, user_id: str, todo_type: TodoType, content: str, priority: int = 0) -> Todo:
        todo = Todo(
            id=str(uuid.uuid4())[:8],
            todo_type=todo_type.value,
            content=content,
            created_at=time.time(),
            priority=priority,
            done=False,
        )
        data = self._load(user_id)
        todos = data.get("todos", [])
        todos.append(todo.to_dict())
        data["todos"] = todos
        self._save(user_id, data)
        return todo

    def mark_todo_done(self, user_id: str, todo_id: str) -> bool:
        data = self._load(user_id)
        todos = data.get("todos", [])
        for t in todos:
            if t.get("id") == todo_id:
                t["done"] = True
                self._save(user_id, data)
                return True
        return False

    def get_active_todos(self, user_id: str) -> List[Todo]:
        return [t for t in self.get_todos(user_id) if not t.done]

    def format_todos_for_prompt(self, user_id: str) -> str:
        todos = self.get_active_todos(user_id)
        if not todos:
            return ""
        lines = []
        for t in todos:
            prefix = "【生理】" if t.todo_type == TodoType.INTERNAL.value else "【关系】"
            lines.append(f"{prefix} {t.content}")
        return "\n".join(lines)

    def cleanup_old_todos(self, user_id: str, max_age_hours: float = 24.0) -> int:
        now = time.time()
        data = self._load(user_id)
        todos = data.get("todos", [])
        before = len(todos)
        todos = [t for t in todos if (now - t.get("created_at", 0)) < max_age_hours * 3600]
        data["todos"] = todos
        self._save(user_id, data)
        return before - len(todos)

    # ---------- Interaction ----------

    def record_interaction(self, user_id: str, mode: InteractionMode, outcome: InteractionOutcome):
        event = InteractionEvent(mode=mode.value, outcome=outcome.value)
        data = self._load(user_id)
        interactions = data.get("interactions", [])
        interactions.append(event.to_dict())
        if len(interactions) > 200:
            interactions = interactions[-200:]
        data["interactions"] = interactions
        self._save(user_id, data)

    def get_today_interactions(self, user_id: str) -> List[InteractionEvent]:
        today = datetime.now().strftime("%Y-%m-%d")
        data = self._load(user_id)
        interactions = data.get("interactions", [])
        result = []
        for i in interactions:
            ts = i.get("timestamp", 0)
            if datetime.fromtimestamp(ts).strftime("%Y-%m-%d") == today:
                result.append(InteractionEvent.from_dict(i))
        return result

    def clear_interactions(self, user_id: str):
        data = self._load(user_id)
        data["interactions"] = []
        self._save(user_id, data)

    # ---------- Consolidation ----------

    def get_consolidations(self, user_id: str) -> List[Consolidation]:
        data = self._load(user_id)
        cons_data = data.get("consolidations", [])
        return [Consolidation.from_dict(c) for c in cons_data]

    def get_last_consolidation(self, user_id: str) -> Optional[Consolidation]:
        cons = self.get_consolidations(user_id)
        return cons[-1] if cons else None

    def run_consolidation(self, user_id: str, date: Optional[str] = None) -> Consolidation:
        target_date = date or datetime.now().strftime("%Y-%m-%d")
        interactions = self.get_today_interactions(user_id)

        connected = sum(1 for i in interactions if i.outcome == InteractionOutcome.CONNECTED.value)
        missed = sum(1 for i in interactions if i.outcome == InteractionOutcome.MISSED.value)
        active = sum(1 for i in interactions if i.mode == InteractionMode.ACTIVE.value)
        passive = sum(1 for i in interactions if i.mode == InteractionMode.PASSIVE.value)
        awkward = sum(1 for i in interactions if i.outcome == InteractionOutcome.AWKWARD.value)
        relief = sum(1 for i in interactions if i.outcome == InteractionOutcome.RELIEF.value)

        if missed >= connected and missed > 0:
            trajectory = "gap"
            shift_hint = "今天有点落差，主动搭话但没被接上"
        elif connected > missed and connected >= 2:
            trajectory = "upward"
            shift_hint = "今天聊得挺开心的"
        elif active == 0 and passive == 0:
            trajectory = "alone"
            shift_hint = "今天没怎么说话"
        elif awkward > relief:
            trajectory = "gap"
            shift_hint = "今天有些尴尬的时刻"
        elif relief > 0:
            trajectory = "steady"
            shift_hint = "今天气氛还算平稳"
        else:
            trajectory = "flat"
            shift_hint = "今天平平淡淡"

        cons = Consolidation(
            date=target_date,
            connected_count=connected,
            missed_count=missed,
            active_count=active,
            passive_count=passive,
            awkward_count=awkward,
            relief_count=relief,
            trajectory=trajectory,
            shift_hint=shift_hint,
        )

        data = self._load(user_id)
        consolidations = data.get("consolidations", [])
        consolidations = [c for c in consolidations if c.get("date") != target_date]
        consolidations.append(cons.to_dict())
        if len(consolidations) > 30:
            consolidations = consolidations[-30:]
        data["consolidations"] = consolidations
        self._save(user_id, data)
        self.clear_interactions(user_id)
        return cons

    # ---------- Admin ----------

    def reset_user(self, user_id: str):
        path = self._file_path(user_id)
        if path.exists():
            path.unlink()
        self._cache.pop(user_id, None)

    def list_users(self) -> List[str]:
        return [f.stem for f in self.data_dir.iterdir() if f.suffix == ".json"]
