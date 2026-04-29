"""
Tests for storage.py — JSON file storage engine
"""

import json
import time
from pathlib import Path

import pytest

from astrbot_plugin_private_persona_counhopig.storage import PersonaStorage
from astrbot_plugin_private_persona_counhopig.models import (
    EmotionState,
    UserProfile,
    TodoType,
    InteractionMode,
    InteractionOutcome,
)


@pytest.fixture
def tmp_storage(tmp_path):
    data_dir = tmp_path / "test_data"
    return PersonaStorage(data_dir)


class TestEmotionStorage:
    def test_get_emotion_default(self, tmp_storage):
        e = tmp_storage.get_emotion("user1")
        assert isinstance(e, EmotionState)
        assert e.energy == 80.0

    def test_save_and_get_emotion(self, tmp_storage):
        e = EmotionState(energy=30, mood=40, social_need=60)
        tmp_storage.save_emotion("user1", e)
        e2 = tmp_storage.get_emotion("user1")
        assert e2.energy == 30.0
        assert e2.mood == 40.0

    def test_apply_decay(self, tmp_storage):
        e = EmotionState(energy=100, mood=100, social_need=0)
        e.last_update = time.time() - 7200  # 2 hours ago
        tmp_storage.save_emotion("user1", e)
        e2 = tmp_storage.apply_decay("user1", decay_per_hour=5.0)
        assert e2.energy == pytest.approx(90.0, abs=0.1)  # 100 - 5*2


class TestProfileStorage:
    def test_get_profile_default(self, tmp_storage):
        p = tmp_storage.get_profile("user1")
        assert p.user_id == "user1"
        assert p.chat_count == 0

    def test_touch_profile(self, tmp_storage):
        p = tmp_storage.touch_profile("user1", nickname="Alice")
        assert p.chat_count == 1
        assert p.nickname == "Alice"
        p2 = tmp_storage.touch_profile("user1", nickname="Bob")
        assert p2.chat_count == 2
        assert p2.nickname == "Alice"  # should not overwrite


class TestMemoryStorage:
    def test_append_and_get_history(self, tmp_storage):
        tmp_storage.append_history("user1", "user", "Hello")
        tmp_storage.append_history("user1", "bot", "Hi there")
        history = tmp_storage.get_history("user1")
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[0].content == "Hello"

    def test_format_history(self, tmp_storage):
        tmp_storage.append_history("user1", "user", "A")
        tmp_storage.append_history("user1", "bot", "B")
        tmp_storage.append_history("user1", "user", "C")
        tmp_storage.append_history("user1", "bot", "D")
        tmp_storage.append_history("user1", "user", "E")
        text = tmp_storage.format_history_for_prompt("user1", max_turns=2)
        assert "用户: E" in text
        assert "你: D" in text
        assert "用户: A" not in text  # exceeded max_turns*2

    def test_history_limit(self, tmp_storage):
        for i in range(105):
            tmp_storage.append_history("user1", "user", str(i))
        history = tmp_storage.get_history("user1")
        assert len(history) == 100


class TestEffectStorage:
    def test_add_and_get_effects(self, tmp_storage):
        e = tmp_storage.add_effect("user1", "lonely", 60, "test", duration_hours=1)
        effects = tmp_storage.get_effects("user1")
        assert len(effects) == 1
        assert effects[0].effect_type == "lonely"

    def test_cleanup_expired(self, tmp_storage):
        now = time.time()
        tmp_storage.add_effect("user1", "old", 50, "old", duration_hours=-1)  # already expired
        tmp_storage.add_effect("user1", "new", 50, "new", duration_hours=10)
        cleaned = tmp_storage.cleanup_expired_effects("user1")
        assert cleaned == 1
        assert len(tmp_storage.get_active_effects("user1")) == 1

    def test_remove_effect(self, tmp_storage):
        e = tmp_storage.add_effect("user1", "tmp", 50, "tmp")
        assert tmp_storage.remove_effect("user1", e.id) is True
        assert tmp_storage.remove_effect("user1", e.id) is False


class TestTodoStorage:
    def test_add_and_get_todos(self, tmp_storage):
        t = tmp_storage.add_todo("user1", TodoType.SOCIAL, "想聊天")
        todos = tmp_storage.get_todos("user1")
        assert len(todos) == 1
        assert todos[0].content == "想聊天"

    def test_mark_done(self, tmp_storage):
        t = tmp_storage.add_todo("user1", TodoType.INTERNAL, "休息")
        assert tmp_storage.mark_todo_done("user1", t.id) is True
        active = tmp_storage.get_active_todos("user1")
        assert len(active) == 0
        assert tmp_storage.mark_todo_done("user1", "nonexistent") is False

    def test_cleanup_old_todos(self, tmp_storage):
        tmp_storage.add_todo("user1", TodoType.SOCIAL, "old", priority=0)
        # manually hack created_at to be old
        data = tmp_storage._load("user1")
        data["todos"][0]["created_at"] = time.time() - 86400 * 2
        tmp_storage._save("user1", data)
        cleaned = tmp_storage.cleanup_old_todos("user1", max_age_hours=24)
        assert cleaned == 1


class TestInteractionStorage:
    def test_record_and_get_today(self, tmp_storage):
        tmp_storage.record_interaction("user1", InteractionMode.PASSIVE, InteractionOutcome.CONNECTED)
        tmp_storage.record_interaction("user1", InteractionMode.PASSIVE, InteractionOutcome.MISSED)
        today = tmp_storage.get_today_interactions("user1")
        assert len(today) == 2
        assert today[0].outcome == InteractionOutcome.CONNECTED.value

    def test_clear_interactions(self, tmp_storage):
        tmp_storage.record_interaction("user1", InteractionMode.ACTIVE, InteractionOutcome.CONNECTED)
        tmp_storage.clear_interactions("user1")
        assert len(tmp_storage.get_today_interactions("user1")) == 0


class TestConsolidationStorage:
    def test_run_consolidation(self, tmp_storage):
        tmp_storage.record_interaction("user1", InteractionMode.PASSIVE, InteractionOutcome.CONNECTED)
        tmp_storage.record_interaction("user1", InteractionMode.PASSIVE, InteractionOutcome.CONNECTED)
        cons = tmp_storage.run_consolidation("user1")
        assert cons.connected_count == 2
        assert cons.trajectory == "upward"
        # interactions should be cleared after consolidation
        assert len(tmp_storage.get_today_interactions("user1")) == 0

    def test_run_consolidation_gap(self, tmp_storage):
        tmp_storage.record_interaction("user1", InteractionMode.PASSIVE, InteractionOutcome.MISSED)
        tmp_storage.record_interaction("user1", InteractionMode.PASSIVE, InteractionOutcome.MISSED)
        cons = tmp_storage.run_consolidation("user1")
        assert cons.trajectory == "gap"

    def test_get_last_consolidation(self, tmp_storage):
        assert tmp_storage.get_last_consolidation("user1") is None
        tmp_storage.run_consolidation("user1")
        last = tmp_storage.get_last_consolidation("user1")
        assert last is not None


class TestAdminStorage:
    def test_reset_user(self, tmp_storage):
        tmp_storage.save_emotion("user1", EmotionState(energy=50))
        tmp_storage.reset_user("user1")
        e = tmp_storage.get_emotion("user1")
        assert e.energy == 80.0  # default

    def test_list_users(self, tmp_storage):
        tmp_storage.save_emotion("user1", EmotionState())
        tmp_storage.save_emotion("user2", EmotionState())
        users = tmp_storage.list_users()
        assert "user1" in users
        assert "user2" in users

    def test_file_path_sanitization(self, tmp_storage):
        path = tmp_storage._file_path("user/../123")
        assert ".." not in str(path)
