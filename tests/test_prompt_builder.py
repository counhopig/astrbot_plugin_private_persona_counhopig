"""
Tests for engine/prompt_builder.py — prompt injection building
"""

from pathlib import Path

import pytest

from astrbot_plugin_private_persona_counhopig.config import PluginConfig
from astrbot_plugin_private_persona_counhopig.storage import PersonaStorage
from astrbot_plugin_private_persona_counhopig.engine.prompt_builder import PromptBuilder
from astrbot_plugin_private_persona_counhopig.models import EmotionState


@pytest.fixture
def builder(tmp_path):
    cfg = PluginConfig({})
    storage = PersonaStorage(tmp_path / "data")
    return PromptBuilder(cfg, storage)


class TestPromptBuilder:
    def test_build_all_returns_list(self, builder):
        injections = builder.build_all("u1")
        assert isinstance(injections, list)
        assert len(injections) > 0

    def test_persona_block_present(self, builder):
        injections = builder.build_all("u1")
        persona_block = [b for b in injections if b.startswith("[人格设定]")]
        assert len(persona_block) == 1
        assert "小忆" in persona_block[0]

    def test_time_block_present(self, builder):
        injections = builder.build_all("u1")
        time_block = [b for b in injections if b.startswith("[时间感知]")]
        assert len(time_block) == 1

    def test_emotion_block_narrative(self, builder):
        builder.cfg.emotion_injection_style = "narrative"
        injections = builder.build_all("u1")
        emotion_block = [b for b in injections if b.startswith("[内心状态]")]
        assert len(emotion_block) == 1

    def test_emotion_block_status(self, builder):
        builder.cfg.emotion_injection_style = "status"
        injections = builder.build_all("u1")
        emotion_block = [b for b in injections if b.startswith("[状态面板]")]
        assert len(emotion_block) == 1

    def test_effect_block_when_no_effects(self, builder):
        injections = builder.build_all("u1")
        effect_blocks = [b for b in injections if b.startswith("[心绪]")]
        assert len(effect_blocks) == 0  # no active effects

    def test_effect_block_when_effects_exist(self, builder):
        builder.storage.add_effect("u1", "lonely", 80, "寂寞了", duration_hours=10)
        injections = builder.build_all("u1")
        effect_blocks = [b for b in injections if b.startswith("[心绪]")]
        assert len(effect_blocks) == 1
        assert "寂寞了" in effect_blocks[0]

    def test_todo_block_when_no_todos(self, builder):
        injections = builder.build_all("u1")
        todo_blocks = [b for b in injections if b.startswith("[脑内关切]")]
        assert len(todo_blocks) == 0

    def test_todo_block_when_todos_exist(self, builder):
        from astrbot_plugin_private_persona_counhopig.models import TodoType
        builder.storage.add_todo("u1", TodoType.SOCIAL, "想聊天")
        injections = builder.build_all("u1")
        todo_blocks = [b for b in injections if b.startswith("[脑内关切]")]
        assert len(todo_blocks) == 1
        assert "想聊天" in todo_blocks[0]

    def test_profile_block_first_chat_empty(self, builder):
        injections = builder.build_all("u1")
        profile_blocks = [b for b in injections if b.startswith("[对用户的印象]")]
        assert len(profile_blocks) == 0  # first chat, no profile yet

    def test_profile_block_after_touch(self, builder):
        builder.storage.touch_profile("u1", nickname="Alice")
        injections = builder.build_all("u1")
        profile_blocks = [b for b in injections if b.startswith("[对用户的印象]")]
        assert len(profile_blocks) == 1
        assert "Alice" in profile_blocks[0]

    def test_history_block_empty_when_no_history(self, builder):
        injections = builder.build_all("u1")
        history_blocks = [b for b in injections if b.startswith("[最近的对话]")]
        assert len(history_blocks) == 0

    def test_history_block_with_history(self, builder):
        builder.storage.append_history("u1", "user", "Hello")
        builder.storage.append_history("u1", "bot", "Hi")
        injections = builder.build_all("u1")
        history_blocks = [b for b in injections if b.startswith("[最近的对话]")]
        assert len(history_blocks) == 1
        assert "Hello" in history_blocks[0]

    def test_style_block_present(self, builder):
        injections = builder.build_all("u1")
        style_blocks = [b for b in injections if b.startswith("[回复风格]")]
        assert len(style_blocks) == 1

    def test_consolidation_block_empty_when_no_consolidation(self, builder):
        injections = builder.build_all("u1")
        cons_blocks = [b for b in injections if b.startswith("[昨日回响]")]
        assert len(cons_blocks) == 0

    def test_disabled_modules_not_injected(self, builder):
        builder.cfg.emotion_enabled = False
        builder.cfg.effect_enabled = False
        builder.cfg.todo_enabled = False
        builder.cfg.profile_enabled = False
        builder.cfg.memory_enabled = False
        builder.cfg.consolidation_enabled = False
        builder.cfg.time_awareness_enabled = False
        builder.cfg.goodnight_hint_enabled = False
        injections = builder.build_all("u1")
        # Only persona + style should remain
        assert len(injections) == 2
