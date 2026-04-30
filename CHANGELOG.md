# Changelog

All notable changes to this project will be documented in this file.

## [2.3.1] - 2026-05-01

### Fixed
- `engine/interaction.py`：`_COLD_KEYWORDS`（"哦/嗯/随便/无所谓"等）此前完全未被 `judge_outcome` 使用，导致冷漠回复被错误判定为 `CONNECTED`，现已补上对应分支，正确返回 `AWKWARD`
- `engine/effect_engine.py`：lonely 检测使用 `get_today_interactions[-1]` 的时间戳，而该记录是刚写入的当前消息，导致 `hours_since ≈ 0`，lonely 永远不触发；现改用 `storage.get_prev_interaction_time()` 获取当前消息**之前**的上一次交互时间
- `storage.py`：`on_llm_response` 中 `append_history` 与 `save_emotion` 两次独立 load+save 合并为 `append_history_and_recover_emotion`，减少一次文件 I/O
- `main.py`：`on_llm_request` 中 `if self.cfg.ignore_group_chat and not is_private: return` 之后紧跟 `if not is_private: return`，前一行是完全多余的死条件，已移除

### Changed
- `storage.py`：`_cache` 从 `dict` 换为 `OrderedDict`，加入 LRU 淘汰上限（`_CACHE_MAX=200`），防止长期运行中内存无限增长

## [2.3.0] - 2025-04-29

### Added
- 自动反思系统（参考 self_evolution）：
  - `engine/reflection_engine.py` — 分析对话历史，生成自我校准记录
  - 触发方式：每 N 轮私聊对话（默认 10 轮）+ AstrBot cron 周期性任务（默认每 6 小时）
  - LLM 输出 JSON：摘要、自评、用户情绪变化、新事实提取、认知纠偏
  - 反思记录自动写入画像事实
- 自动画像构建系统：
  - `engine/profile_builder.py` — 从对话中提取用户偏好/身份/习惯/情绪模式
  - 触发方式：每 N 轮私聊对话（默认 5 轮）
  - 画像事实自动去重（category + content），保留最近 50 条
  - 事实注入 Prompt，Bot 回复时自然引用
- `upsert_cognitive_memory` LLM 工具 — LLM 在对话中主动调用记录新发现
- 新命令：
  - `/persona_reflections` — 查看反思记录
  - `/persona_facts` — 查看自动构建的画像事实
  - `/persona_clear_reflections` — 清空反思
  - `/persona_remove_fact <ID>` — 删除画像事实
- 新配置项（AstrBot 后台）：
  - `reflection_enabled` / `reflection_trigger_turns` / `reflection_history_turns` / `reflection_periodic_cron`
  - `profile_building_enabled` / `profile_building_trigger_turns`

## [2.2.0] - 2025-04-29

### Added
- 手动修改工具命令集（无需重启，即时生效）:
  - `/persona_set_emotion <e> <m> <s>` — 直接设置情感状态
  - `/persona_set_affinity <0~100>` — 直接设置好感度
  - `/persona_set_nickname <昵称>` — 修改昵称
  - `/persona_set_config <key> <value>` — 动态修改配置（管理员）
  - `/persona_remove_effect <ID>` — 删除指定心绪
  - `/persona_clear_effects` — 清空所有心绪
  - `/persona_clear_todos` — 清空所有待办
  - `/persona_history` — 查看最近对话历史
  - `/persona_debug` — 查看原始 JSON 数据（管理员）

## [2.1.0] - 2025-04-29

### Added
- 74 个单元测试（pytest），覆盖 models / storage / engine / commands
- `tests/conftest.py` mock astrbot.api，支持无框架环境测试

### Fixed
- `on_llm_response` 中 `response` 为 LLMResponse 对象而非 str，导致 TypeError
- `engine/interaction.py` 相对导入路径错误（`.models` → `..models`）

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
