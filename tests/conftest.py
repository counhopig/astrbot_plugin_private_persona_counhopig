"""
测试基础：mock astrbot.api 依赖
"""

import sys
from types import ModuleType
from unittest.mock import MagicMock

# 构建 astrbot.api mock 树
_astrbot = ModuleType("astrbot")
_api = ModuleType("astrbot.api")
_api.logger = MagicMock()
_api.logger.debug = MagicMock()
_api.logger.info = MagicMock()
_api.logger.warning = MagicMock()
_api.logger.error = MagicMock()

_astrbot.api = _api
sys.modules["astrbot"] = _astrbot
sys.modules["astrbot.api"] = _api

# mock astrbot.api.event
_event_mod = ModuleType("astrbot.api.event")
_event_mod.filter = MagicMock()
_event_mod.AstrMessageEvent = MagicMock()
_astrbot.api.event = _event_mod
sys.modules["astrbot.api.event"] = _event_mod

# mock astrbot.api.provider
_provider_mod = ModuleType("astrbot.api.provider")
_provider_mod.ProviderRequest = MagicMock()
_astrbot.api.provider = _provider_mod
sys.modules["astrbot.api.provider"] = _provider_mod

# mock astrbot.api.star
_star_mod = ModuleType("astrbot.api.star")
_star_mod.Context = MagicMock()
_star_mod.Star = object
_star_mod.register = lambda *a, **k: lambda cls: cls
_astrbot.api.star = _star_mod
sys.modules["astrbot.api.star"] = _star_mod
