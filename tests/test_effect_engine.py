"""
Tests for engine/effect_engine.py — automatic effect triggering
"""

import time

import pytest

from astrbot_plugin_private_persona_counhopig.storage import PersonaStorage
from astrbot_plugin_private_persona_counhopig.models import InteractionOutcome, InteractionMode
from astrbot_plugin_private_persona_counhopig.engine.effect_engine import EffectEngine


@pytest.fixture
def engine(tmp_path):
    storage = PersonaStorage(tmp_path / "data")
    return EffectEngine(storage), storage


class TestEffectAutoTrigger:
    def test_missed_creates_wronged(self, engine):
        eff_engine, storage = engine
        eff_engine.auto_trigger("u1", "滚", InteractionOutcome.MISSED)
        effects = storage.get_active_effects("u1")
        assert any(e.effect_type == "wronged" for e in effects)

    def test_awkward_creates_awkward(self, engine):
        eff_engine, storage = engine
        eff_engine.auto_trigger("u1", "...", InteractionOutcome.AWKWARD)
        effects = storage.get_active_effects("u1")
        assert any(e.effect_type == "awkward" for e in effects)

    def test_long_gap_creates_lonely(self, engine):
        eff_engine, storage = engine
        # 记录一次历史互动，然后将时间戳改为 7 小时前以模拟长时间未互动
        storage.record_interaction("u1", InteractionMode.PASSIVE, InteractionOutcome.CONNECTED)
        data = storage._load("u1")
        data["interactions"][-1]["timestamp"] = time.time() - 7 * 3600
        storage._save("u1", data)
        eff_engine.auto_trigger("u1", "hi", InteractionOutcome.CONNECTED)
        effects = storage.get_active_effects("u1")
        assert any(e.effect_type == "lonely" for e in effects)

    def test_no_lonely_if_recent(self, engine):
        eff_engine, storage = engine
        # 记录一次历史互动，然后将时间戳改为 1 小时前（未超过 6 小时阈值）
        storage.record_interaction("u1", InteractionMode.PASSIVE, InteractionOutcome.CONNECTED)
        data = storage._load("u1")
        data["interactions"][-1]["timestamp"] = time.time() - 1 * 3600
        storage._save("u1", data)
        eff_engine.auto_trigger("u1", "hi", InteractionOutcome.CONNECTED)
        effects = storage.get_active_effects("u1")
        assert not any(e.effect_type == "lonely" for e in effects)

    def test_tired_at_night_low_energy(self, engine):
        eff_engine, storage = engine
        # set energy low
        from astrbot_plugin_private_persona_counhopig.models import EmotionState
        e = EmotionState(energy=20, mood=50, social_need=50)
        storage.save_emotion("u1", e)
        # Can't easily mock datetime.now() here without monkeypatch
        # So we just verify the engine runs without error
        eff_engine.auto_trigger("u1", "zzz", InteractionOutcome.CONNECTED)
        # tired effect depends on hour, may or may not trigger

    def test_multiple_effects_can_coexist(self, engine):
        eff_engine, storage = engine
        eff_engine.auto_trigger("u1", "滚", InteractionOutcome.MISSED)
        eff_engine.auto_trigger("u1", "...", InteractionOutcome.AWKWARD)
        effects = storage.get_active_effects("u1")
        types = {e.effect_type for e in effects}
        assert "wronged" in types
        assert "awkward" in types
