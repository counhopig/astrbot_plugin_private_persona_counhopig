"""
Tests for engine/interaction.py — outcome judgment
"""


from astrbot_plugin_private_persona_counhopig.engine.interaction import judge_outcome
from astrbot_plugin_private_persona_counhopig.models import InteractionOutcome


class TestJudgeOutcome:
    def test_hostile_returns_missed(self):
        assert judge_outcome("滚开") == InteractionOutcome.MISSED
        assert judge_outcome("别烦我") == InteractionOutcome.MISSED
        assert judge_outcome("闭嘴") == InteractionOutcome.MISSED

    def test_friendly_returns_connected(self):
        assert judge_outcome("谢谢！") == InteractionOutcome.CONNECTED
        assert judge_outcome("哈哈") == InteractionOutcome.CONNECTED
        assert judge_outcome("晚安") == InteractionOutcome.CONNECTED

    def test_short_message_returns_awkward(self):
        assert judge_outcome("哦") == InteractionOutcome.AWKWARD
        assert judge_outcome("嗯") == InteractionOutcome.AWKWARD
        assert judge_outcome("a") == InteractionOutcome.AWKWARD
        assert judge_outcome("  ") == InteractionOutcome.AWKWARD

    def test_neutral_returns_connected(self):
        assert judge_outcome("今天天气不错") == InteractionOutcome.CONNECTED
        assert judge_outcome("你在干嘛") == InteractionOutcome.CONNECTED

    def test_case_insensitive(self):
        assert judge_outcome("HAHA") == InteractionOutcome.CONNECTED
        assert judge_outcome("haha") == InteractionOutcome.CONNECTED
        assert judge_outcome("滚") == InteractionOutcome.MISSED

    def test_friendly_overrides_short(self):
        # "好" is 1 char (<=2, would be AWKWARD) but also in FRIENDLY
        # Actually "好" is in _FRIENDLY_KEYWORDS? Let me check...
        # Wait, "好" is not in FRIENDLY, but "好的" is
        assert judge_outcome("好的") == InteractionOutcome.CONNECTED

    def test_hostile_overrides_friendly(self):
        # If message contains both hostile and friendly keywords
        # hostile is checked first
        assert judge_outcome("哈哈滚") == InteractionOutcome.MISSED
