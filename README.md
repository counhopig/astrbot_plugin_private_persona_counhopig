# AstrBot 私聊人格插件

为 AstrBot 的**私聊场景**注入可配置的人格、情感状态、Effect、Todo 与日结。

本插件参考 [astrbot_plugin_self_evolution](https://github.com/Renyus/astrbot_plugin_self_evolution) 的 Persona Sim / Effect / Todo / Consolidation 架构，聚焦私聊单人陪伴场景，去掉群聊复杂度与重量级依赖，提供开箱即用的"人格生活模拟"体验。

---

## 与 self_evolution 的关系

| | 本插件 | self_evolution |
|---|---|---|
| **定位** | 私聊专属，轻量陪伴 | 群聊 + 私聊，全功能进化 |
| **存储** | 每用户一个 JSON 文件 | SQLite + AstrBot 知识库 |
| **部署门槛** | 低，无额外依赖 | 需配置知识库、NapCat 等 |
| **人格状态** | 活力 / 心情 / 社交需求（三维） | 活力 / 心情 / 社交需求 / 饱腹感（四维） |
| **Effect 心绪** | ✅ 来源语义 + 衰减风格 | ✅ 同源机制，存 SQLite |
| **Todo 脑内关切** | ✅ 生理型 + 关系型 | ✅ 同源机制 |
| **日结轨迹** | ✅ | ✅ |
| **对话记忆** | ✅ 本地历史记录 | ✅ 知识库长期召回 |
| **用户画像** | ✅ 本地 JSON | ✅ 本地文件 + 自动构建 |
| **自动反思** | ✅ 轮数触发 + cron 定时 | ✅ 每日反思批处理 |
| **主动插嘴** | ❌ | ✅ Active Engagement 4.0 |
| **人格弧线** | ❌ | ✅ Persona Arc（阶段养成） |
| **表情包学习** | ❌ | ✅ |
| **群消息审核** | ❌ | ✅ |
| **戳一戳互动** | ❌ | ✅ |
| **SAN 精力系统** | ❌（由情感系统替代） | ✅ SAN × Persona Sim 统一 |

> **选哪个？** 如果你只需要私聊陪伴、不想搭建知识库和 SQLite、希望快速上手，选本插件。如果你需要群聊互动、主动插嘴、人格养成和完整的记忆系统，选 self_evolution。

---

## 功能

| 功能 | 说明 |
|------|------|
| **人格注入** | 在私聊 LLM 请求时自动注入人格基底、回复风格 |
| **情感系统** | 活力 / 心情 / 社交需求，随时间自然衰减，互动后恢复 |
| **Effect 心绪** | 互动触发心绪效果（wronged/lonely/tired/awkward），带来源语义与自然衰减 |
| **Todo 脑内关切** | 生理型（need_todo）与关系型（social_todo）待办，注入 Prompt 影响行为 |
| **日结轨迹** | 每日互动统计与情感轨迹（向上/有落差/独处/平淡/平稳），次日注入回响 |
| **对话记忆** | 自动记录最近 N 轮对话，作为上下文注入 Prompt |
| **用户画像** | 维护聊天次数、昵称、好感度、备注 |
| **自动反思** | 每隔 N 轮对话触发 LLM 自我反思，提取用户新事实、纠偏已有认知，可配置周期性 cron |
| **画像构建** | 每隔 N 轮自动从对话中提取用户特征事实，补充到用户画像并注入 Prompt |
| **时间感知** | 根据当前时段（早晨/深夜等）注入场景提示 |
| **群聊隔离** | 可配置只在私聊生效，不影响群聊行为 |

---

## 安装

1. 将本插件文件夹复制到 AstrBot 的 `plugins/` 目录下。
2. 重启 AstrBot，或在管理后台重载插件。
3. 进入 **插件配置 → 私聊人格**，修改人格设定、开关与阈值。

---

## 命令

### 状态查看

| 命令 | 别名 | 说明 |
|------|------|------|
| `/persona` | `/人格` `/pg` | 查看完整人格状态（情感、Effect、Todo、画像、记忆、日结） |
| `/persona_effects` | `/心绪` `/pfx` | 查看活跃 Effect 列表 |
| `/persona_todo` | `/待办` `/pft` | 查看脑内待办列表 |
| `/persona_today` | `/今日人格` `/ptd` | 查看今日互动摘要（日结预览） |

### 日结与管理

| 命令 | 别名 | 说明 |
|------|------|------|
| `/persona_consolidate` | `/日结` `/pcn` | 手动执行人格日结 |
| `/persona_apply <类型>` | `/人格影响` `/pap` | 手动应用互动影响（bad/awkward/normal/good/relief） |
| `/persona_add_effect <类型> <描述>` | `/添加心绪` `/pafe` | 手动添加 Effect（管理员） |
| `/persona_remove_effect <ID>` | `/删除心绪` `/prfe` | 删除指定心绪 |
| `/persona_clear_effects` | `/清空心绪` `/pcfe` | 清空所有活跃心绪 |
| `/persona_add_todo <need/social> <内容>` | `/添加待办` `/pat` | 手动添加 Todo |
| `/persona_done_todo <ID>` | `/完成待办` `/pdt` | 标记 Todo 完成 |
| `/persona_clear_todos` | `/清空待办` `/pctd` | 清空所有脑内关切 |
| `/persona_set_emotion <活力> <心情> <社交需求>` | `/设置情感` `/pse` | 手动设置情感三维数值（0~100） |
| `/persona_reset` | `/人格重置` `/pgr` | 重置当前用户的所有记忆和状态 |
| `/persona_note` | `/人格备注` `/pgn` | 添加/查看用户备注 |
| `/persona_affinity [+/-数值]` | `/好感度` `/pgaf` | 查看好感度（管理员可调整） |
| `/persona_set_affinity <数值>` | `/设置好感度` `/psaf` | 直接设置好感度绝对值（0~100） |
| `/persona_help` | `/人格帮助` `/pgh` | 显示帮助 |

---

## 配置项

在 AstrBot 管理后台的 `_conf_schema.json` 可视化界面中配置：

### 人格设定
- **Bot 名称** — 私聊中对自己的称呼
- **人格基底 Prompt** — 核心性格描述
- **回复风格提示** — 控制语气、长度、emoji 使用
- **时间感知** — 注入当前时段提示

### 情感系统
- **启用情感系统** — 总开关
- **每小时自然衰减** — 能量/心情的下降速度
- **每次回复恢复量** — 互动后的恢复值
- **情感注入风格** — `narrative`（叙事型）或 `status`（状态型）

### 心绪 Effect
- **启用 Effect 系统** — 总开关
- **自动触发 Effect** — 根据互动结果自动产生心绪

### 脑内待办
- **启用 Todo 系统** — 总开关
- **自动触发 Todo** — 根据状态和 Effect 自动生成待办

### 人格日结
- **启用日结系统** — 总开关，开启后昨日回响会注入今日 Prompt

### 私聊记忆
- **启用记忆系统** — 总开关
- **记忆轮数** — 注入 Prompt 的最近对话轮数
- **启用用户画像** — 维护用户偏好与特征

### 自动反思
- **启用反思系统** — 总开关，开启后每隔 N 轮对话自动调用 LLM 进行自我反思
- **触发轮数** — 每隔多少轮对话触发一次反思（默认 10）
- **反思历史轮数** — 反思时参考的最近对话条数（默认 20）
- **周期性 cron** — 除轮数触发外，额外的 cron 定时反思（默认 `0 */6 * * *`，留空禁用）

### 画像构建
- **启用画像构建** — 总开关，开启后每隔 N 轮自动从对话中提取用户事实
- **触发轮数** — 每隔多少轮对话触发一次画像构建（默认 5）

### 行为控制
- **仅在私聊生效** — 开启后群聊不受影响
- **首次私聊问候** — 第一次私聊时的特殊处理
- **夜间温柔提示** — 深夜时段注入晚安氛围

### 存储与调试
- **缓存最大用户数** — 内存缓存的最大用户数（默认 200）
- **调试日志** — 开启后在控制台输出详细的 Debug 日志

---

## 项目结构

```
astrbot_plugin_private_persona_counhopig/
├── main.py                    # 插件入口：生命周期、事件监听、命令路由
├── config.py                  # 配置解析
├── models.py                  # 数据模型：所有 Enum + Dataclass
├── storage.py                 # JSON 存储引擎
├── metadata.yaml              # 插件元数据
├── _conf_schema.json          # 可视化配置
├── CHANGELOG.md
├── README.md
├── requirements.txt
├── .gitignore
│
├── engine/                    # 核心引擎层
│   ├── prompt_builder.py      # Prompt 注入构建
│   ├── interaction.py         # 互动判定
│   ├── effect_engine.py       # Effect 自动触发规则
│   ├── todo_engine.py         # Todo 自动触发规则
│   ├── reflection_engine.py   # 自动反思：对话分析、事实提取、认知纠偏
│   ├── profile_builder.py     # 画像构建：从对话中提取用户特征
│   └── utils.py               # 工具函数
│
└── commands/
    └── handlers.py            # 命令响应逻辑
```

---

## 数据存储

所有数据以 JSON 文件形式存放在插件目录的 `data/` 下，每个用户一个文件：

```
data/
├── 123456789.json      # 用户数据（情感、画像、历史、Effect、Todo、Interaction、Consolidation）
└── 987654321.json
```

---

## 设计思路

参考 `self_evolution` 的架构，针对私聊场景做了以下适配：

1. **去掉群聊复杂度** — 只关注私聊，不处理多人上下文、主动插嘴、群消息审核等群聊特有逻辑。
2. **去掉 SQLite / 知识库** — 用轻量 JSON 文件替代 SQLite 和 AstrBot 知识库，零配置即可运行。
3. **保留 Effect/Todo/日结核心** — 完整移植 Persona Sim 的心绪起伏与脑内关切机制，让 Bot 有情绪连贯性。
4. **新增自动反思** — 每隔 N 轮或定时通过 LLM 对对话进行反思，提取用户新事实、纠偏认知，持久化后注入后续 Prompt（对应 self_evolution 的每日反思批处理，但以轮数+cron 双触发替代纯定时）。
5. **新增画像构建** — 自动从对话中提炼用户特征事实，持久化后在每次对话中作为上下文注入（对应 self_evolution 的 auto_profile）。
6. **情感三维** — 沿用活力/心情/社交需求，去掉 self_evolution 的饱腹感（satiety），降低状态复杂度。
7. **模块化结构** — models / storage / config / engine / commands / main，职责分离，方便二次开发。

目标是：**让 Bot 在私聊中像一个有记忆、有情绪、有性格、有心绪起伏的个体，而不是每次对话都是一张白纸。**

---

## License

MIT
