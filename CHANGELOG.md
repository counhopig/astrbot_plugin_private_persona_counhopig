# 更新日志

本项目所有值得注意的更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)，本项目遵循 [语义化版本规范](https://semver.org/spec/v2.0.0.html)。

## [2.8.4] - 2026-05-09

### 修复
- `main.py`：主动问候 cron 无法触发——不再依赖被动创建的 lonely effect
  - `_proactive_nudge()` 之前通过 `get_active_effects()` 扫描已有的 lonely effect，但 lonely effect 只在用户发消息时由 `effect_engine` 被动创建，导致 cron 永远抓不到沉默用户
  - 修复为通过 `storage.py` 新增的 `get_hours_since_last_interaction()` 直接根据持久化的 interactions 记录计算孤独时长，与 `effect_engine` 保持相同 6h 阈值、60% 强度阈值（≥12h）
  - 问候后追加 `record_interaction()` 防止同一 cron 周期重复问候
- `storage.py`：新增 `get_hours_since_last_interaction()` 方法，基于持久化 interactions 记录返回距上次交互的小时数，`profile.last_seen` 作为回退

## [2.8.3] - 2026-05-07

### 修复
- `main.py`：修复 `_extract_text()` 无法从 AstrBot `LLMResponse` 中提取文本的 bug
  - 新增对 `completion_text` 属性的检查，优先于旧版 `completion` / `choices` 路径
  - 此前 `LLMResponse` 不具备 `completion` 或 `choices` 属性，导致 fallback 到 `str(response)`，将整个 dataclass（含 `reasoning_content`）输出给用户
  - 同时修复了 `_proactive_nudge`、`on_llm_response`、`_run_reflection`、`_run_profile_building` 四处因同原因导致的文本提取失败

## [2.8.2] - 2026-05-07

### 修复
- `storage.py`：修复缓存键不一致导致情感状态显示冻结的 bug
  - `_load` / `_save` 中的缓存字典 key 改为统一使用规范化的 user_id（去除 `@`、`.` 等特殊字符），与 `_file_path` 的文件命名规则一致
  - 此前 cron 任务 `_periodic_emotion_decay` 传入的 user_id（文件 stem）与事件处理器传入的完整 WeChat ID 被视为不同缓存 key，cron 更新文件后 `/persona` 命令仍命中旧缓存，导致活力/心情/社交需求显示值长时间不变
- `tests/test_prompt_builder.py`：修复 `test_disabled_modules_not_injected` 遗漏禁用 `greeting_on_first_chat` 导致的断言失败

## [2.8.1] - 2026-05-03

### 修复
- `main.py`：修复 cron 僵尸任务累积问题，导致 AstrBot 日志每 30 分钟出现 `RuntimeError: Basic cron job handler not found` 错误的 bug
  - 新增 `_cleanup_stale_cron_jobs()`，在 `initialize()` 和 `on_plugin_unloaded()` 中自动清理本插件遗留的旧 cron 任务（根据 job name 匹配）
  - 解决了配置变更（如 cron 表达式修改）后旧 job 残留、handler 丢失导致调度器反复执行失败的罕见 bug
  - 同时修复了 `main.py` 中 `@register` 装饰器版本号（`2.7.0` → `2.8.1`）与 `metadata.yaml` 不一致的历史问题

## [2.8.0] - 2026-05-02

### 新增
- `main.py`：新增情感衰减 cron 任务 `_periodic_emotion_decay`，按 `emotion_decay_cron`（默认每小时）遍历所有用户执行 `apply_decay`，解决无对话时状态静止的问题
- `config.py`：新增 `emotion_decay_cron` 配置项（默认 `0 * * * *`）
- `_conf_schema.json`：新增"情感衰减定时任务"配置说明，可在 AstrBot 后台调整频率或留空禁用

## [2.7.1] - 2026-05-01

### 变更
- `main.py`：数据目录切换为 AstrBot 框架规范目录（`plugin_data`），优先通过 `StarTools.get_data_dir("astrbot_plugin_private_persona_counhopig")` 获取，避免写入插件源码目录
- `README.md`：数据存储路径说明由 `data/` 更新为 `plugin_data/`
- `.gitignore`：新增 `plugin_data/` 忽略规则

### 新增
- `main.py`：新增旧目录数据迁移逻辑，启动时自动将本地 `data/` 下尚未迁移的用户 JSON 文件移动到 `plugin_data`，确保升级后数据连续

## [2.7.0] - 2026-05-01

### 新增
- 插件互联 API：`main.py` 暴露 `get_emotion(user_id)` / `get_affinity(user_id)` / `get_persona_snapshot(user_id)`，供其他 AstrBot 插件读取人格状态
- `storage.py`：新增 `get_affinity(user_id)` 与 `get_persona_snapshot(user_id)`，统一输出纯 JSON 可消费数据结构，降低跨插件集成成本
- `tests/test_storage.py`：新增互联 API 相关单元测试，覆盖好感度读取与人格快照输出

## [2.6.0] - 2026-05-01

### 新增
- `storage.py`：新增 `save_umo(user_id, umo)` / `get_umo(user_id)`，将用户的 `unified_msg_origin` 持久化，为主动推送提供基础
- `main.py`：`on_message_listener` 中在每次私聊时自动保存用户 UMO
- `main.py`：新增主动问候 cron 任务 `_proactive_nudge_job` / `_proactive_nudge`
  - 每小时扫描所有有 lonely effect 且强度 >= 60% 的用户
  - 调用 LLM 以角色身份生成一条自然的主动问候消息
  - 通过 `context.send_message(umo, MessageChain)` 主动推送给用户
  - 问候后自动移除 lonely effect、恢复情感能量，避免重复推送
  - 每用户之间 sleep 1s，避免并发 LLM 请求风暴
- `config.py`：新增 `proactive_nudge_enabled`（默认 true）和 `proactive_nudge_cron`（默认 `0 * * * *`）
- `_conf_schema.json`：新增"启用主动问候"和"主动问候检测频率"两项配置说明

## [2.5.0] - 2026-05-01

### 新增
- `engine/prompt_builder.py`：新增 `_first_chat_hint()`，当用户 `chat_count <= 1` 时向 LLM 注入首次见面指引，引导其自然自我介绍并告知 `/persona_help` 入口
- `main.py`：实现 `on_first_chat_greeting()`，修复原来的空占位函数——首次私聊时立即发送固定欢迎消息（含 help 提示），修正了竞争条件（由 `chat_count > 1` 改为 `== 0`）
- `engine/prompt_builder.py`：Effect 自然流露增强——心绪强度 > 50% 时在 Prompt 末尾追加「自然流露」引导，避免 LLM 直接说出状态名称
- `engine/prompt_builder.py`：好感度称谓系统——affinity 四段映射具名关系阶段（陌生人 / 普通朋友 / 好朋友 / 知己），影响 LLM 回复的亲密度与语气
- `engine/prompt_builder.py`：里程碑纪念日 Prompt 提示——聊天满 10 / 50 / 100 / 200 / 500 次时注入纪念日提示，由 LLM 自然提及
- `commands/handlers.py`：`cmd_apply` 新增中文参数支持（负面 / 尴尬 / 普通 / 正面 / 化解），与英文关键字完全等价
- `commands/handlers.py`：`cmd_help` 全面重构——按「查看状态 / 反思与画像 / 日结 / 手动调整 / 高级管理员」分组，每条指令标注快捷别名，文案面向普通用户
- `main.py`：`persona_help` 指令新增 `help` 和 `?` 别名，降低新用户发现帮助的门槛

### 变更
- `engine/prompt_builder.py`：`import time` 补充，`_effect()` 重构以支持心绪强度判断

## [2.4.0] - 2026-05-01

### 新增
- `storage.py`：`PersonaStorage.__init__` 新增 `cache_max` 参数，允许外部配置 LRU 缓存上限
- `config.py`：新增 `storage_cache_max` 配置项（默认 200），通过 AstrBot 后台即可调整缓存大小
- `storage.py`：新增 `increment_turn_counter` / `reset_turn_counter` / `get_turn_counter`，将反思与画像构建的轮数计数器持久化到用户 JSON，插件重启后不再丢失计数
- `engine/utils.py`：提取公共 `extract_json` 函数，统一 LLM 输出的 JSON 解析逻辑
- `models.py`：新增 `_safe_from_dict` 兼容性反序列化辅助函数，加载旧格式数据时自动忽略未知字段，支持数据模型向前演进

### 修复
- `engine/effect_engine.py`：新增 `_has_active_effect` 去重检查，避免同一类型的 Effect（wronged / awkward / lonely / tired）重复叠加
- `engine/interaction.py`：`_COLD_KEYWORDS` 改为精确匹配（`_COLD_EXACT`），"好"等单字只在消息完全等于该词时才判为 AWKWARD，大幅降低误判率
- `main.py`：`_turn_counters` / `_profile_turn_counters` 由内存 dict 改为持久化存储，`InteractionMode` 提前到模块顶层导入
- `tests/test_effect_engine.py`：修复 lonely 相关测试，改用 `record_interaction` + `_prev_interaction_times` 而非已废弃的 `profile.last_seen`

### 变更
- `engine/profile_builder.py`、`engine/reflection_engine.py`：内联的 `_extract_json` 统一替换为 `engine/utils.extract_json`，消除重复代码
- `models.py`：所有 dataclass 的 `from_dict` 改用 `_safe_from_dict`，提升数据兼容性

## [2.3.1] - 2026-05-01

### 修复
- `engine/interaction.py`：`_COLD_KEYWORDS`（"哦/嗯/随便/无所谓"等）此前完全未被 `judge_outcome` 使用，导致冷漠回复被错误判定为 `CONNECTED`，现已补上对应分支，正确返回 `AWKWARD`
- `engine/effect_engine.py`：lonely 检测使用 `get_today_interactions[-1]` 的时间戳，而该记录是刚写入的当前消息，导致 `hours_since ≈ 0`，lonely 永远不触发；现改用 `storage.get_prev_interaction_time()` 获取当前消息**之前**的上一次交互时间
- `storage.py`：`on_llm_response` 中 `append_history` 与 `save_emotion` 两次独立 load+save 合并为 `append_history_and_recover_emotion`，减少一次文件 I/O
- `main.py`：`on_llm_request` 中 `if self.cfg.ignore_group_chat and not is_private: return` 之后紧跟 `if not is_private: return`，前一行是完全多余的死条件，已移除

### 变更
- `storage.py`：`_cache` 从 `dict` 换为 `OrderedDict`，加入 LRU 淘汰上限（`_CACHE_MAX=200`），防止长期运行中内存无限增长

## [2.3.0] - 2025-04-29

### 新增
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

### 新增
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

### 新增
- 74 个单元测试（pytest），覆盖 models / storage / engine / commands
- `tests/conftest.py` mock astrbot.api，支持无框架环境测试

### 修复
- `on_llm_response` 中 `response` 为 LLMResponse 对象而非 str，导致 TypeError
- `engine/interaction.py` 相对导入路径错误（`.models` -> `..models`）

## [2.0.0] - 2025-04-29

### 新增
- Effect/Todo/Consolidation 系统（参考 self_evolution）
- `engine/` 模块拆分：prompt_builder, interaction, effect_engine, todo_engine
- `commands/` 模块拆分：handlers
- `models.py` 独立数据模型层
- `storage.py` 独立存储引擎
- `config.py` 独立配置解析

### 变更
- 项目结构重构，职责分离
- 插件名改为 `astrbot_plugin_private_persona_counhopig`

## [1.0.0] - 2025-04-29

### 新增
- 初始版本：私聊人格注入
- 情感系统（energy/mood/social_need）
- 对话记忆与用户画像
- 时间感知与夜间提示
- 基础命令集（/persona, /persona_reset, /persona_note, /persona_affinity, /persona_help）
