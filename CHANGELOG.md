# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2025-04-29

### Added
- Effect/Todo/Consolidation 系统（参考 self_evolution）
- `engine/` 模块拆分：prompt_builder, interaction, effect_engine, todo_engine
- `commands/` 模块拆分：handlers
- `models.py` 独立数据模型层
- `storage.py` 独立存储引擎
- `config.py` 独立配置解析

### Changed
- 项目结构重构，职责分离
- 插件名改为 `astrbot_plugin_private_persona_counhopig`

## [1.0.0] - 2025-04-29

### Added
- 初始版本：私聊人格注入
- 情感系统（energy/mood/social_need）
- 对话记忆与用户画像
- 时间感知与夜间提示
- 基础命令集（/persona, /persona_reset, /persona_note, /persona_affinity, /persona_help）
