"""
数据模型层：枚举与 dataclass
所有插件内共享的数据结构定义。
"""

import time
import uuid
from dataclasses import dataclass, field, asdict, fields as dc_fields
from datetime import datetime
from enum import Enum


def _safe_from_dict(cls, d: dict):
    """兼容性反序列化：忽略 d 中多余的 key，允许数据模型向前演进。"""
    known = {f.name for f in dc_fields(cls)}
    return cls(**{k: v for k, v in d.items() if k in known})


# ============================================================
# Enums
# ============================================================

class TodoType(Enum):
    INTERNAL = "need_todo"    # 生理型：饿、累、想安静
    SOCIAL = "social_todo"    # 关系型：想把话说完、想继续聊


class InteractionMode(Enum):
    ACTIVE = "active"         # Bot 主动搭话
    PASSIVE = "passive"       # Bot 被动回应


class InteractionOutcome(Enum):
    CONNECTED = "connected"   # 互动成功
    MISSED = "missed"         # 被冷落 / 期望落空
    AWKWARD = "awkward"       # 尴尬
    RELIEF = "relief"         # 轻松化解


# ============================================================
# Dataclasses
# ============================================================

@dataclass
class EmotionState:
    """Bot 的内在情感状态"""
    energy: float = 80.0
    mood: float = 70.0
    social_need: float = 50.0
    last_update: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "EmotionState":
        return _safe_from_dict(cls, d)

    def decay(self, amount: float):
        self.energy = max(0.0, self.energy - amount)
        self.mood = max(0.0, self.mood - amount * 0.8)
        self.social_need = min(100.0, self.social_need + amount * 0.5)
        self.last_update = time.time()

    def on_interact(self, recovery: float):
        self.energy = min(100.0, self.energy + recovery)
        self.mood = min(100.0, self.mood + recovery * 1.2)
        self.social_need = max(0.0, self.social_need - recovery)
        self.last_update = time.time()

    def narrative(self) -> str:
        parts = []
        if self.energy < 20:
            parts.append("累到不想动")
        elif self.energy < 50:
            parts.append("有点疲惫")
        elif self.energy > 80:
            parts.append("精力充沛")

        if self.mood < 20:
            parts.append("心情低落")
        elif self.mood < 50:
            parts.append("兴致不高")
        elif self.mood > 80:
            parts.append("心情很好")

        if self.social_need > 80:
            parts.append("很想找人说话")
        elif self.social_need > 50:
            parts.append("有点想聊天")

        if not parts:
            return "状态平稳"
        return "，".join(parts)

    def status_str(self) -> str:
        return f"活力: {self.energy:.0f}/100 | 心情: {self.mood:.0f}/100 | 社交需求: {self.social_need:.0f}/100"


@dataclass
class UserProfile:
    user_id: str
    nickname: str = ""
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    chat_count: int = 0
    notes: str = ""
    affinity: float = 50.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "UserProfile":
        return _safe_from_dict(cls, d)


@dataclass
class ChatTurn:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ChatTurn":
        return _safe_from_dict(cls, d)


@dataclass
class Effect:
    """情感 Effect，携带来源语义"""
    id: str
    effect_type: str
    intensity: float
    source_detail: str
    decay_style: str
    recovery_style: str
    created_at: float
    expires_at: float

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Effect":
        return _safe_from_dict(cls, d)

    def current_intensity(self, now: float) -> float:
        if now >= self.expires_at:
            return 0.0
        total = self.expires_at - self.created_at
        if total <= 0:
            return self.intensity
        elapsed = now - self.created_at
        ratio = elapsed / total

        if self.decay_style == "fast":
            if ratio < 0.3:
                return self.intensity * (1 - ratio / 0.3 * 0.8)
            else:
                return self.intensity * 0.2 * (1 - (ratio - 0.3) / 0.7)
        elif self.decay_style == "slow":
            if ratio < 0.5:
                return self.intensity * (1 - ratio)
            else:
                return self.intensity * 0.5 * (1 - (ratio - 0.5) / 0.5 * 0.5)
        else:
            return self.intensity * (1 - ratio)

    def narrative(self, now: float) -> str:
        intensity = self.current_intensity(now)
        if intensity < 10:
            return ""
        if intensity > 60:
            strength = "强烈"
        elif intensity > 30:
            strength = "有些"
        else:
            strength = "淡淡的"
        return f"{strength}{self.source_detail}"


@dataclass
class Todo:
    """脑内待办"""
    id: str
    todo_type: str
    content: str
    created_at: float
    priority: int = 0
    done: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Todo":
        return _safe_from_dict(cls, d)


@dataclass
class InteractionEvent:
    mode: str
    outcome: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "InteractionEvent":
        return _safe_from_dict(cls, d)


@dataclass
class Consolidation:
    """人格日结"""
    date: str
    connected_count: int = 0
    missed_count: int = 0
    active_count: int = 0
    passive_count: int = 0
    awkward_count: int = 0
    relief_count: int = 0
    trajectory: str = "flat"
    shift_hint: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Consolidation":
        return _safe_from_dict(cls, d)


@dataclass
class ProfileFact:
    """画像事实：自动提取的用户特征/偏好"""
    id: str
    category: str           # e.g. "preference", "identity", "habit", "emotion"
    content: str            # 事实内容
    evidence: str           # 来源证据（对话原文）
    confidence: float = 1.0 # 置信度 0~1
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ProfileFact":
        return _safe_from_dict(cls, d)


@dataclass
class ReflectionRecord:
    """反思记录：LLM 对对话的自我校准"""
    id: str
    trigger: str            # 触发原因：auto / manual / periodic
    note: str               # 反思内容
    facts_str: str = ""     # 提取的事实（|分隔）
    bias: str = ""          # 认知纠偏
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ReflectionRecord":
        return _safe_from_dict(cls, d)

    def explicit_facts(self) -> list[str]:
        """解析 facts_str 为列表"""
        if not self.facts_str:
            return []
        return [f.strip() for f in self.facts_str.split("|") if f.strip()]


@dataclass
class ReflectionSession:
    """一次反思会话的上下文"""
    user_id: str
    messages: list[dict]    # 参与反思的对话历史
    summary: str = ""       # LLM 生成的摘要
    reflection_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ReflectionSession":
        return _safe_from_dict(cls, d)
