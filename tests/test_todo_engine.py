"""
Tests for engine/todo_engine.py — automatic todo triggering
"""

import time
from pathlib import Path

import pytest

from astrbot_plugin_private_persona_counhopig.storage import PersonaStorage
from astrbot_plugin_private_persona_counhopig.models import (
    EmotionState,
    InteractionOutcome,
    TodoType,
)
from astrbot_plugin_private_persona_counhopig.engine.todo_engine import TodoEngine


@pytest.fixture
def engine(tmp_path):
    storage = PersonaStorage(tmp_path / "data")
    return TodoEngine(storage), storage


class TestTodoAutoTrigger:
    def test_tired_low_energy_creates_need_todo(self, engine):
        todo_engine, storage = engine
        # create tired effect + low energy
        storage.add_effect("u1", "tired", 70, "夜深了", duration_hours=10)
        storage.save_emotion("u1", EmotionState(energy=20, mood=50, social_need=50))
        todo_engine.auto_trigger("u1", "test", InteractionOutcome.CONNECTED)
        todos = storage.get_active_todos("u1")
        assert any(t.content == "想休息一下" for t in todos)

    def test_wronged_and_missed_creates_social_todo(self, engine):
        todo_engine, storage = engine
        storage.add_effect("u1", "wronged", 70, "被冷落", duration_hours=10)
        todo_engine.auto_trigger("u1", "test", InteractionOutcome.MISSED)
        todos = storage.get_active_todos("u1")
        assert any(t.content == "想把当时没说完的话接上" for t in todos)

    def test_lonely_high_social_need_creates_chat_todo(self, engine):
        todo_engine, storage = engine
        storage.add_effect("u1", "lonely", 70, "寂寞", duration_hours=10)
        storage.save_emotion("u1", EmotionState(energy=50, mood=50, social_need=70))
        todo_engine.auto_trigger("u1", "test", InteractionOutcome.CONNECTED)
        todos = storage.get_active_todos("u1")
        assert any(t.content == "想找人聊聊天" for t in todos)

    def test_no_duplicate_todos(self, engine):
        todo_engine, storage = engine
        storage.add_effect("u1", "wronged", 70, "被冷落", duration_hours=10)
        todo_engine.auto_trigger("u1", "test", InteractionOutcome.MISSED)
        todo_engine.auto_trigger("u1", "test", InteractionOutcome.MISSED)
        todos = storage.get_active_todos("u1")
        assert len([t for t in todos if t.content == "想把当时没说完的话接上"]) == 1

    def test_no_todo_without_matching_effect(self, engine):
        todo_engine, storage = engine
        storage.save_emotion("u1", EmotionState(energy=20, mood=50, social_need=50))
        # no tired effect, so no need_todo
        todo_engine.auto_trigger("u1", "test", InteractionOutcome.CONNECTED)
        todos = storage.get_active_todos("u1")
        assert len(todos) == 0
