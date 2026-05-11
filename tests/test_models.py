"""
Tests for models.py — data models and enums
"""

import time


from astrbot_plugin_private_persona_counhopig.models import (
    EmotionState,
    Effect,
    Todo,
    TodoType,
    InteractionOutcome,
)


class TestEmotionState:
    def test_default_values(self):
        e = EmotionState()
        assert e.energy == 80.0
        assert e.mood == 70.0
        assert e.social_need == 50.0

    def test_decay_reduces_energy_and_mood(self):
        e = EmotionState(energy=100, mood=100, social_need=0)
        e.decay(10)
        assert e.energy == 90.0
        assert e.mood == 92.0  # 100 - 10*0.8
        assert e.social_need == 5.0  # 0 + 10*0.5

    def test_decay_clamps_at_zero(self):
        e = EmotionState(energy=5, mood=5)
        e.decay(100)
        assert e.energy == 0.0
        assert e.mood == 0.0

    def test_on_interact_recover(self):
        e = EmotionState(energy=50, mood=50, social_need=80)
        e.on_interact(10)
        assert e.energy == 60.0
        assert e.mood == 62.0  # 50 + 10*1.2
        assert e.social_need == 70.0

    def test_on_interact_clamps(self):
        e = EmotionState(energy=95, mood=95, social_need=5)
        e.on_interact(10)
        assert e.energy == 100.0
        assert e.mood == 100.0
        assert e.social_need == 0.0

    def test_narrative_when_low(self):
        e = EmotionState(energy=10, mood=10, social_need=90)
        text = e.narrative()
        assert "累到不想动" in text
        assert "心情低落" in text
        assert "很想找人说话" in text

    def test_narrative_when_high(self):
        e = EmotionState(energy=90, mood=90, social_need=10)
        text = e.narrative()
        assert "精力充沛" in text
        assert "心情很好" in text

    def test_narrative_when_mixed(self):
        e = EmotionState(energy=60, mood=60, social_need=50)
        text = e.narrative()
        # 60 is between 50~80 for all, so no narrative
        assert text == "状态平稳"

    def test_to_dict_roundtrip(self):
        e = EmotionState(energy=55, mood=66, social_need=77)
        d = e.to_dict()
        e2 = EmotionState.from_dict(d)
        assert e2.energy == 55.0
        assert e2.mood == 66.0
        assert e2.social_need == 77.0


class TestEffect:
    def test_current_intensity_linear(self):
        now = time.time()
        e = Effect(
            id="test",
            effect_type="lonely",
            intensity=100,
            source_detail="test",
            decay_style="linear",
            recovery_style="social",
            created_at=now,
            expires_at=now + 3600,
        )
        assert e.current_intensity(now) == 100.0
        assert e.current_intensity(now + 1800) == 50.0
        assert e.current_intensity(now + 3600) == 0.0

    def test_current_intensity_after_expiry(self):
        now = time.time()
        e = Effect(
            id="test",
            effect_type="tired",
            intensity=100,
            source_detail="test",
            decay_style="linear",
            recovery_style="sleep",
            created_at=now,
            expires_at=now + 100,
        )
        assert e.current_intensity(now + 200) == 0.0

    def test_narrative_high_intensity(self):
        now = time.time()
        e = Effect(
            id="test",
            effect_type="wronged",
            intensity=80,
            source_detail="被冷落了",
            decay_style="linear",
            recovery_style="social",
            created_at=now,
            expires_at=now + 3600,
        )
        assert "强烈被冷落了" in e.narrative(now)

    def test_narrative_fades_below_threshold(self):
        now = time.time()
        e = Effect(
            id="test",
            effect_type="wronged",
            intensity=80,
            source_detail="被冷落了",
            decay_style="linear",
            recovery_style="social",
            created_at=now,
            expires_at=now + 3600,
        )
        assert e.narrative(now + 3500) == ""  # intensity < 10

    def test_to_dict_roundtrip(self):
        now = time.time()
        e = Effect(
            id="abc",
            effect_type="excited",
            intensity=70,
            source_detail="收到了礼物",
            decay_style="slow",
            recovery_style="social",
            created_at=now,
            expires_at=now + 7200,
        )
        d = e.to_dict()
        e2 = Effect.from_dict(d)
        assert e2.effect_type == "excited"
        assert e2.intensity == 70.0
        assert e2.source_detail == "收到了礼物"


class TestTodo:
    def test_default_not_done(self):
        t = Todo(id="t1", todo_type=TodoType.SOCIAL.value, content="想聊天", created_at=time.time())
        assert t.done is False

    def test_priority(self):
        t = Todo(id="t1", todo_type=TodoType.INTERNAL.value, content="休息", created_at=time.time(), priority=3)
        assert t.priority == 3

    def test_to_dict_roundtrip(self):
        now = time.time()
        t = Todo(id="t1", todo_type=TodoType.SOCIAL.value, content="想聊天", created_at=now, priority=2, done=True)
        d = t.to_dict()
        t2 = Todo.from_dict(d)
        assert t2.content == "想聊天"
        assert t2.done is True
        assert t2.priority == 2


class TestInteractionOutcome:
    def test_enum_values(self):
        assert InteractionOutcome.CONNECTED.value == "connected"
        assert InteractionOutcome.MISSED.value == "missed"
        assert InteractionOutcome.AWKWARD.value == "awkward"
        assert InteractionOutcome.RELIEF.value == "relief"
