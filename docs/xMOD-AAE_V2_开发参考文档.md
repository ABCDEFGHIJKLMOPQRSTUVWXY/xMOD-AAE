# xMOD-AAE V2 开发参考文档

> AI 有声阅读引擎（Windows/macOS）
>
> 本文档基于当前 xMOD-AAE V1 实现、当前开发模块文档，以及已确认的 V2 升级方向整理。
>
> **V2 的核心目标不是重写整个项目，而是解决 V1 在长篇小说分析中由于文本切分和上下文不足导致的说话人识别、角色归属和角色画像不准确问题。**

---

# 1. 项目定位

xMOD-AAE 是一个桌面端 AI 有声阅读引擎，当前已经具备：

- TXT 导入
- 编码检测
- 章节切分
- 对话/旁白识别
- LLM 说话人识别
- 角色聚合与画像
- 角色→音色映射
- Edge TTS / MiMo TTS
- 音频缓存
- 后台预加载
- pygame 播放
- PyQt6 阅读界面
- SQLite 持久化

当前 V1 的基础运行链路为：

```text
TXT
 ↓
encoding
 ↓
chapter
 ↓
dialogue
 ↓
identify_speakers
 ↓
normalize_speakers
 ↓
collect
 ↓
analyze_characters
 ↓
assign_voice
 ↓
TTS
 ↓
Cache
 ↓
Player
```

当前项目已经具有比较完整的运行基础，因此 V2 **不推倒重来**。

V2 主要增加并重构：

```text
文本结构化分析
        ↓
语义切分
        ↓
Context 构建
        ↓
持续 Narrative State
        ↓
Character Resolution
        ↓
Speaker Attribution
        ↓
Validation
        ↓
Knowledge Base
        ↓
现有 TTS Runtime
```

---

# 2. V1 当前架构

当前项目目录：

```text
xMOD-AAE/
├── Plan.md
├── requirements.txt
├── docs/
│   └── MODULES.md
├── src/
│   ├── main.py
│   ├── config.py
│   ├── secret_store.py
│   ├── text_processor/
│   │   ├── encoding.py
│   │   ├── chapter.py
│   │   └── dialogue.py
│   ├── character_engine/
│   │   ├── aggregator.py
│   │   ├── speaker_normalizer.py
│   │   ├── llm_analyzer.py
│   │   ├── voice_design.py
│   │   ├── voice_mapper.py
│   │   └── character_store.py
│   ├── tts_engine/
│   │   ├── voice_registry.py
│   │   ├── edge_tts_client.py
│   │   ├── audio_converter.py
│   │   ├── cache_manager.py
│   │   ├── segment_builder.py
│   │   └── drivers/
│   │       ├── base.py
│   │       ├── manager.py
│   │       ├── edge_tts_driver.py
│   │       └── mimo_driver.py
│   ├── player/
│   │   ├── chunk_queue.py
│   │   ├── audio_player.py
│   │   └── playback_controller.py
│   └── ui/
│       ├── main_window.py
│       ├── bookshelf.py
│       ├── chapter_list.py
│       ├── reader_view.py
│       ├── control_bar.py
│       ├── character_panel.py
│       └── settings_dialog.py
└── tests/
```

当前模块职责和已有实现见现有模块文档。当前文本处理、角色分析、TTS、播放器、UI 和测试均已经有明确接口。 

---

# 3. V1 当前核心问题

## 3.1 固定 Batch 不符合小说语义

当前角色分析使用：

```text
段落数 ≤ 5
且
累计字符数 ≤ 6000
```

才组成一个 LLM 批次。

这个策略可以控制 API 请求规模，但它不是语义切分。

小说可能在边界处发生：

```text
A：“你真的决定了吗？”

[Chunk Boundary]

“那就算了。”
```

第二句话脱离上下文后无法可靠判断说话人。

因此：

> V2 不应简单地把 6000 改成更大的数字或更小的数字。

真正需要解决的是：

**文本分析块的边界与小说语义边界不一致。**

---

## 3.2 Chunk 与 Context 混为一体

V1 更接近：

```text
Chunk = LLM Input
```

V2 应改成：

```text
Analysis Chunk
+
Context Window
+
Memory
+
Narrative State
=
LLM Input
```

其中：

- Analysis Chunk：真正需要产生分析结果的正文
- Context Window：帮助模型判断当前文本的前后文
- Memory：长期/近期已知信息
- Narrative State：小说目前的发展状态

---

## 3.3 角色是字符串，不是稳定实体

V1 中角色主要以姓名/称呼字符串存在。

长篇小说中可能出现：

```text
李耀
李师兄
师兄
少年
他
```

这些可能全部指向：

```text
character_id = char_001
```

V2 必须建立：

```text
Character ID
+
Alias
+
Entity Resolution
```

---

## 3.4 “对话是谁说的”与“哪里是对话”需要分离

文本解析负责：

```text
Dialogue / Narration
```

LLM 负责：

```text
Speaker Attribution
```

二者不能继续过度耦合。

---

## 3.5 缺少持续 Narrative State

V1 每一批文本更像独立分析。

V2 应当让分析过程随着小说推进持续维护：

```text
Block 1
 ↓
State Update

Block 2
 ↓
State Update

Block 3
 ↓
State Update

...
```

系统最终掌握的不是简单的“已读到第 N 块”，而是：

- 当前人物
- 当前场景
- 当前人物关系
- 当前事件
- 最近状态
- 已知事实
- 最近上下文

---

# 4. V2 核心设计目标

V2 必须优先解决以下问题：

1. 语义切分
2. Chunk / Context 分离
3. Character ID + Alias
4. Scene
5. Narrative State
6. Speaker Attribution
7. Confidence
8. Validation
9. Memory Compression / Retrieval
10. 局部重新分析
11. Analysis Version

其中：

- 1～9：V2 核心分析能力
- 10～11：V2 需要规划并支持

以下方向暂缓：

- 二次分析 / 强模型复核机制
- 更复杂的 Narrative Intelligence 扩展
- 作者风格指纹等高级能力

---

# 5. V2 总体架构

建议演进为：

```text
                         xMOD-AAE
                            │
             ┌──────────────┴──────────────┐
             │                             │
             ▼                             ▼
      Novel Intelligence              Audio Runtime
             │                             │
             │                     ┌───────┼────────┐
             │                     │       │        │
             │                     ▼       ▼        ▼
             │                    TTS    Cache    Player
             │                     │       │        │
             │                     └───────┴────────┘
             │
     ┌───────┼────────┬───────────┐
     ▼       ▼        ▼           ▼
   Text   Character  Scene     Narrative
 Engine    Engine    Engine      State
     │       │        │           │
     └───────┴────────┴───────────┘
                     │
                     ▼
               Context Builder
                     │
                     ▼
              LLM Structured Analysis
                     │
          ┌──────────┼───────────┐
          ▼          ▼           ▼
      Speaker     Character     Scene/
     Attribution Resolution      State
          │          │           │
          └──────────┼───────────┘
                     ▼
                  Validator
                     │
                     ▼
              Knowledge Base
                     │
                     ▼
               Speech/TTS Layer
```

---

# 6. 核心原则

## 6.1 V1 Runtime 尽量不动

以下模块原则上保留：

- `tts_engine/drivers`
- `cache_manager`
- `chunk_queue`
- `audio_player`
- `playback_controller`
- Edge TTS
- MiMo TTS
- voice registry
- 基础 UI 播放功能

它们已经形成稳定运行链路。

---

## 6.2 重点重构分析层

主要重构：

```text
text_processor/
character_engine/
MainWindow 中的分析编排
character_store
```

主要新增：

```text
analysis_pipeline/
storage/
narrative/
```

---

## 6.3 Knowledge 与 Context 分离

必须遵守：

> 忘的是 Prompt Context，不是小说知识。

例如角色 100 章没有出现：

```text
Active Context:
不携带

Knowledge Base:
仍然完整保存
```

第 180 章再次出现：

```text
Entity Detection
 ↓
Character Retrieval
 ↓
重新进入 Active Context
```

---

# 7. 文本分析 Pipeline

最终建议：

```text
TXT
 ↓
Encoding
 ↓
Chapter Detection
 ↓
Paragraph Structure
 ↓
Dialogue/Narration Parsing
 ↓
Scene Boundary Detection
 ↓
Semantic Chunk Builder
 ↓
Context Builder
 ↓
LLM Analysis
 ↓
Validation
 ↓
State Update
 ↓
Knowledge Base
```

---

# 8. Semantic Chunk Builder

## 8.1 基本策略

保留当前方案：

```text
target ≈ 5000 字
overlap ≈ 500 字
```

但 5000 字不是硬边界。

切分优先级：

```text
1. 章节边界
2. 场景边界
3. 段落边界
4. 连续对话组边界
5. 句子边界
6. 最终才使用硬字符边界
```

建议允许：

```text
min ≈ 3000
target ≈ 5000
max ≈ 6500
```

具体参数以后通过真实小说测试集调优。

---

## 8.2 Overlap

Overlap 用于：

- 跨 Chunk 对话衔接
- 代词指代判断
- 当前场景判断
- 上下文连续性

但：

> Overlap 文本不应被重复计入新的角色特征、事件统计或正文分析结果。

每段文本必须拥有稳定的：

```text
global_start
global_end
```

或等价的稳定 ID。

---

# 9. Chunk 与 Context 分离

建议定义：

```python
AnalysisChunk
```

包含：

```text
chunk_id
book_id
chapter_id
sequence
text
global_start
global_end
scene_ids
```

另外定义：

```python
ContextWindow
```

包含：

```text
previous_text
current_text
next_text
active_characters
active_scene
narrative_state
recent_dialogue
retrieved_memory
```

最终：

```text
AnalysisChunk
      +
ContextWindow
      ↓
LLM
```

只有 `AnalysisChunk` 产生正式分析结果。

---

# 10. Dialogue / Narration

现有 `dialogue.py` 的规则解析继续保留。

现有能力包括：

- 引号匹配
- 冒号说话人模式
- 重叠消解
- 旁白/对话区间转换
- 原文还原校验

V2 不应让 LLM 重复完成这些确定性任务。

原则：

```text
规则引擎：
“这是不是对白？”

LLM：
“这是谁说的？”
```

---

# 11. Character Entity System

## 11.1 Character

建议核心结构：

```text
Character
├── character_id
├── canonical_name
├── aliases
├── gender
├── age_group
├── role_type
├── personality
├── speaking_style
├── voice_profile
├── summary
├── first_seen
├── last_seen
├── appearance_count
├── status
└── pinned
```

---

## 11.2 Alias

Alias 不应成为独立角色。

例如：

```text
Character:
char_001

canonical_name:
李耀

aliases:
李师兄
师兄
少年
他
```

但：

> “他”这种代词需要结合上下文解析，不能简单全局注册为永久 Alias。

---

## 11.3 Entity Resolution

流程：

```text
文本
 ↓
候选实体
 ↓
Alias / 称呼匹配
 ↓
当前 Scene 人物
 ↓
最近 Context
 ↓
Character ID
```

如果无法可靠判断：

```text
character_id = unresolved
confidence < threshold
```

不要强行创建新角色。

---

# 12. Scene 系统

Scene 是 V2 新增的核心实体。

建议：

```text
Scene
├── scene_id
├── chapter_id
├── start_offset
├── end_offset
├── location
├── time_context
├── characters
├── summary
├── current_event
├── emotional_context
└── confidence
```

Scene 主要解决：

- 谁在场
- 对话发生在哪里
- 当前发生什么
- 人物关系是什么
- 情绪上下文是什么

---

# 13. Narrative State

Narrative State 是跨 Chunk 持续更新的状态。

第一版不要做得过度复杂。

建议包含：

```text
NarrativeState
├── current_chapter
├── current_scene
├── active_characters
├── relationship_updates
├── major_events
├── recent_summary
├── recent_dialogue
└── important_facts
```

未来可以继续扩展。

---

# 14. Speaker Attribution

这是 V2 最核心的功能之一。

输入：

```text
当前 Dialogue Segment
+
Scene
+
Character Candidates
+
Recent Context
+
Narrative State
```

输出：

```json
{
  "speaker_id": "char_001",
  "confidence": 0.94
}
```

不要只返回：

```json
{
  "speaker": "李耀"
}
```

---

## 14.1 Speaker 判断原则

优先利用：

1. 明示说话人
2. 对话前后的叙述动作
3. 当前 Scene 中的人物
4. 连续对话关系
5. 人物称呼
6. 最近对话
7. Character relationship
8. Narrative State

而不是只依赖当前 5000 字正文。

---

# 15. Confidence

所有关键 LLM 判断应允许附带置信度：

```text
speaker_confidence
character_confidence
scene_confidence
```

第一版可以采用：

```text
0.0 ~ 1.0
```

建议：

```text
>= 0.80
可靠

0.50 ~ 0.79
需要记录为低置信度结果

< 0.50
标记为疑难结果
```

当前阶段：

> 不自动引入复杂二次分析。

低置信度结果先进入数据库，供 Validation 和后续局部重新分析使用。

---

# 16. Validation

LLM 结果不得直接写入最终 Knowledge Base。

建议：

```text
LLM Output
 ↓
JSON Parse
 ↓
Schema Validation
 ↓
Semantic Validation
 ↓
State Conflict Check
 ↓
Commit
```

检查：

### JSON

- 是否为合法 JSON
- 字段是否完整
- 类型是否正确

### Speaker

- speaker_id 是否存在
- 是否声明为新角色
- 是否与当前 Scene 冲突

### Character

- 是否产生无依据新角色
- Alias 是否冲突
- Character ID 是否稳定

### Dialogue

- 是否覆盖当前需要分析的对白
- 是否出现重复/遗漏

### State

- 是否出现明显冲突
- 是否覆盖已有事实

---

# 17. Memory Compression / Retrieval

建议采用：

```text
Knowledge Base
      │
      ├── Active Memory
      │
      └── Cold Knowledge
```

而不是实际删除。

---

## 17.1 Active Memory

当前 Prompt 主要携带：

```text
S级 / Pin 核心角色
+
当前 Scene 人物
+
最近出现角色
+
当前相关关系
+
最近摘要
+
必要事实
```

---

## 17.2 Cold Knowledge

长期未出现角色、历史事件、旧状态等保留在 SQLite。

需要时：

```text
Entity Detection
 ↓
Retrieval
 ↓
Wake
 ↓
Context Injection
```

---

## 17.3 Memory Budget

原方案的 `memory_budget` 保留。

但实现时建议优先按 token 控制，而不是单纯按中文字符数。

例如：

```yaml
memory:
  budget_tokens: 2000
```

实际数值以后根据模型和真实小说测试调整。

---

# 18. LLM Structured Output

建议第一版输出：

```json
{
  "block_summary": "本块核心事件摘要",
  "scenes": [
    {
      "scene_id": "scene_local_001",
      "summary": "场景摘要",
      "location": "地点",
      "characters": ["char_001", "char_002"]
    }
  ],
  "dialogues": [
    {
      "segment_id": "seg_001",
      "speaker_id": "char_001",
      "speaker_name": "李耀",
      "confidence": 0.94,
      "text": "你真的决定了吗？",
      "tone": "迟疑"
    }
  ],
  "new_characters": [],
  "character_updates": [],
  "relationship_updates": [],
  "events": [],
  "facts": []
}
```

注意：

> `segment_id` 应来自程序，而不是让 LLM 自己发明正文定位。

---

# 19. 数据库设计

V1 当前 SQLite 主要包含：

```text
books
characters
voice_map
settings
```

V2 建议逐步增加：

```text
books
chapters
segments
scenes
characters
character_aliases
character_states
relationships
narrative_states
analysis_results
processing_history
memory_items
archive
detective_board
analysis_versions
```

其中：

- `detective_board` 可以先预留
- `style_fingerprint` 暂缓
- 复杂知识图谱暂缓

---

# 20. 推荐的核心数据表

## books

```text
id
title
file_path
author
created_at
updated_at
current_analysis_version_id
```

## chapters

```text
id
book_id
chapter_index
title
start_offset
end_offset
content_hash
```

## segments

```text
id
chapter_id
segment_index
type
text
start_offset
end_offset
speaker_id
scene_id
```

## characters

```text
id
book_id
canonical_name
gender
age_group
role_type
personality
speaking_style
summary
voice_id
voice_params
first_seen
last_seen
appearance_count
status
pinned
```

## character_aliases

```text
id
character_id
alias
alias_type
confidence
source
```

## scenes

```text
id
book_id
chapter_id
scene_index
start_offset
end_offset
location
time_context
summary
current_event
emotional_context
confidence
```

## character_states

```text
id
character_id
scene_id
state_type
state_value
source_segment_id
created_at
```

## relationships

```text
id
book_id
character_a
character_b
relationship_type
status
confidence
source_segment_id
updated_at
```

## narrative_states

```text
id
book_id
chunk_id
current_scene_id
summary
state_json
created_at
```

## analysis_results

```text
id
book_id
chunk_id
analysis_version_id
result_json
status
confidence
created_at
```

## processing_history

```text
id
book_id
chunk_id
stage
status
started_at
finished_at
error_message
```

## memory_items

```text
id
book_id
item_type
entity_id
content
priority
last_used_chunk
status
```

## analysis_versions

```text
id
book_id
version_name
model_name
prompt_version
analyzer_version
created_at
status
```

---

# 21. SQLite 迁移原则

继续沿用 V1 的：

> 幂等迁移。

禁止要求用户删除旧数据库。

推荐：

```text
PRAGMA user_version
```

或现有 `_ensure_column()` 机制逐步迁移。

升级原则：

```text
V1 DB
 ↓
Migration
 ↓
V2 DB
```

旧的：

```text
characters
voice_map
settings
books
```

必须继续可用。

---

# 22. Character Engine 重构建议

V1：

```text
identify_speakers
 ↓
normalize_speakers
 ↓
collect
 ↓
analyze_characters
```

V2：

```text
Text Structure
 ↓
Candidate Entity Extraction
 ↓
Character Resolution
 ↓
Scene Resolution
 ↓
Speaker Attribution
 ↓
Character State Update
 ↓
Character Profile Update
```

原有：

```text
aggregator.py
speaker_normalizer.py
llm_analyzer.py
```

不必立即删除。

可以逐步迁移。

---

# 23. 建议新增 analysis_pipeline

建议目录：

```text
src/
├── analysis_pipeline/
│   ├── models.py
│   ├── pipeline.py
│   ├── chunk_builder.py
│   ├── context_builder.py
│   ├── analyzer.py
│   ├── validator.py
│   ├── state_manager.py
│   ├── memory_manager.py
│   └── version_manager.py
```

职责：

### `models.py`

定义：

```text
AnalysisChunk
ContextWindow
AnalysisResult
SpeakerAssignment
```

### `chunk_builder.py`

负责语义切分。

### `context_builder.py`

负责：

```text
Memory
+
Narrative State
+
Scene
+
Overlap
```

### `analyzer.py`

负责调用 LLM。

### `validator.py`

负责验证 LLM 输出。

### `state_manager.py`

负责更新 Narrative State。

### `memory_manager.py`

负责 Active / Cold Memory。

### `version_manager.py`

负责分析版本。

---

# 24. UI 架构调整

当前 `MainWindow` 承担较多业务编排。

V2 不应该继续把：

```text
Chunk
Memory
Scene
Narrative State
LLM
Validation
```

全部放入 `main_window.py`。

推荐：

```text
UI
 ↓
Application Service
 ↓
Analysis Pipeline
 ↓
Storage
```

UI 只负责：

- 开始分析
- 停止分析
- 显示进度
- 显示结果
- 查看角色
- 查看 Scene
- 查看分析状态
- 触发局部重新分析

---

# 25. 局部重新分析

V2 支持：

```text
章节 / Scene / Segment
        ↓
重新构建 Context
        ↓
重新调用分析
        ↓
Validation
        ↓
更新 Knowledge Base
```

例如：

```text
第 47 章
某句 speaker 错误
 ↓
用户选择“重新分析此处”
 ↓
加载前后文
 ↓
加载人物 / Scene / Narrative State
 ↓
重新分析
 ↓
更新结果
```

暂时不要求自动二次分析。

---

# 26. Analysis Version

每次分析应该记录：

```text
Book
Analysis Version
 ├── Model
 ├── Prompt Version
 ├── Analyzer Version
 └── Created At
```

例如：

```text
Analysis v1
Model: deepseek-chat
Prompt: speaker-v1.0
Analyzer: 0.1

Analysis v2
Model: xiaomi-mimo-v2.5
Prompt: speaker-v2.0
Analyzer: 0.2
```

这样可以：

- 比较分析结果
- 重新分析
- 调试 Prompt
- 升级模型
- 保留历史版本

---

# 27. TTS 层改造策略

V2 当前阶段不要大规模修改 TTS。

保留：

```text
Speech Segment
 ↓
segment_builder
 ↓
ChunkInfo
 ↓
TTSDriver
```

未来可以逐步增加：

```text
SpeechPlan
```

但当前核心仍然是：

> 先把 Speaker / Character / Scene 判断正确。

---

# 28. TTS 缓存升级方向

V1 当前缓存键已经包含：

```text
driver_id
voice
voice_params
text
speed
```

V2 可以逐步扩展：

```text
text
+
speaker_id
+
voice
+
voice_params
+
speech_plan
+
driver
```

确保：

```text
同一句话
+
不同角色
+
不同情绪
```

不会错误复用同一音频。

---

# 29. 测试策略

V2 测试重点必须从“单函数测试”进一步扩展到：

> **小说分析场景测试。**

---

## 29.1 单元测试

继续测试：

```text
dialogue
chunk_builder
speaker_normalizer
character_mapper
cache
validator
```

---

## 29.2 Pipeline 测试

建立固定测试文本：

```text
Test Novel A
```

覆盖：

### Case 1

明确：

```text
张三：“你好。”
```

### Case 2

动作指代：

```text
张三看着李四。

“你来了。”
```

### Case 3

连续对白：

```text
“你来了。”
“嗯。”
“最近好吗？”
```

### Case 4

跨 Chunk：

```text
Chunk A:
“你真的要走吗？”

Chunk B:
“那就算了。”
```

### Case 5

Alias：

```text
李耀
李师兄
师兄
少年
```

必须归到同一 Character。

### Case 6

Scene 切换：

```text
地点 A
 ↓
地点 B
```

### Case 7

长期沉睡角色：

```text
Block 1 出现
Block 100 再次出现
```

验证 Cold Knowledge → Retrieval。

---

# 30. 分析准确率指标

V2 开发过程中必须建立可量化指标。

至少记录：

```text
Speaker Accuracy
Character Resolution Accuracy
Dialogue Coverage
Unknown Speaker Rate
Unknown Character Rate
Scene Accuracy
Validation Failure Rate
```

重点指标：

### Speaker Accuracy

```text
正确 Speaker / 总测试 Dialogue
```

### Character Resolution Accuracy

```text
正确 Character ID / 总实体引用
```

### Unknown Rate

```text
无法识别 Speaker / 总 Dialogue
```

---

# 31. 性能指标

记录：

```text
每章分析耗时
每 Chunk API 耗时
平均输入 Token
平均输出 Token
API 请求次数
Retry 次数
Validation Failure
缓存命中率
```

这能帮助判断：

```text
5000 / 500
```

是否真的合理。

---

# 32. Config 建议

V2 可以将配置扩展为：

```yaml
api:
  base_url: "https://api.deepseek.com/v1"
  api_key: "${DEEPSEEK_API_KEY}"
  model_name: "deepseek-chat"
  timeout_seconds: 120

processing:
  chunk_target_size: 5000
  chunk_min_size: 3000
  chunk_max_size: 6500
  overlap_size: 500

memory:
  budget_tokens: 2000
  active_character_limit: 20

analysis:
  enable_scene_analysis: true
  enable_narrative_state: true
  enable_validation: true
  confidence_threshold: 0.8

project:
  protagonist_whitelist:
    - "李耀"
```

注意：

> 具体默认值仍需通过真实小说测试后调整。

---

# 33. V2 开发阶段规划

## Phase 1：数据模型

目标：

```text
Character ID
Alias
Scene
AnalysisChunk
NarrativeState
AnalysisResult
```

先把数据结构定下来。

---

## Phase 2：Semantic Chunk Builder

目标：

```text
章节
 ↓
场景/段落/对话边界
 ↓
5000 字目标
 ↓
500 overlap
```

重点测试跨边界对白。

---

## Phase 3：Context Builder

建立：

```text
AnalysisChunk
+
Previous Context
+
Active Characters
+
Scene
+
Narrative State
+
Retrieved Memory
```

---

## Phase 4：Speaker Attribution

替换当前：

```text
identify_speakers
```

逐步升级为：

```text
Speaker Attribution
```

输出：

```text
speaker_id
confidence
```

---

## Phase 5：Character Resolution

实现：

```text
canonical name
+
alias
+
称呼
+
当前 Scene
+
Narrative State
```

统一 Character ID。

---

## Phase 6：Validation

加入：

```text
Schema Validation
Semantic Validation
Character Validation
Dialogue Coverage
```

---

## Phase 7：Narrative State

每个 Chunk：

```text
Analysis
 ↓
State Update
 ↓
Memory Update
```

形成连续阅读状态。

---

## Phase 8：Memory Compression / Retrieval

实现：

```text
Active
Cold
Retrieval
```

避免 Prompt 无限增长。

---

## Phase 9：局部重新分析

支持：

```text
Segment / Scene / Chunk
 ↓
Re-analysis
```

---

## Phase 10：Analysis Version

支持：

```text
版本
模型
Prompt
Analyzer
```

追踪与重新分析。

---

# 34. V2 暂缓事项

明确不作为当前开发重点：

## 1. 自动二次分析

暂时不做：

```text
低置信度
 ↓
自动切换强模型
```

只保留：

```text
confidence
```

为未来功能预留。

---

## 2. 高级 Narrative Intelligence

暂时不做：

- 完整知识图谱
- 复杂因果图
- 自动时间线推理
- 高级世界观推理

---

## 3. 作者风格指纹

暂缓：

```text
Style Fingerprint
```

未来再增加。

---

# 35. Detective Board

可以在数据模型上预留：

```text
detective_board
```

但只在需要时启用。

未来：

```text
FACT
HYPOTHESIS
RESOLVED
REJECTED
CONFIDENCE
PIN
```

当前不作为普通小说分析的核心流程。

---

# 36. V2 最终数据流

完整目标：

```text
                      TXT
                       │
                       ▼
                   Encoding
                       │
                       ▼
                  Chapter Split
                       │
                       ▼
             Dialogue / Narration
                       │
                       ▼
               Scene Detection
                       │
                       ▼
             Semantic Chunk Builder
                       │
                       ▼
                  AnalysisChunk
                       │
             ┌─────────┼──────────┐
             ▼         ▼          ▼
          Previous   Narrative   Memory
          Context     State      Retrieval
             │         │          │
             └─────────┼──────────┘
                       ▼
                 Context Builder
                       │
                       ▼
                 LLM Analyzer
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       Speaker      Character      Scene
     Attribution    Resolution     Update
          │            │            │
          └────────────┼────────────┘
                       ▼
                    Validate
                       │
                       ▼
               Knowledge Base
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
       Narrative State       Active Memory
             │                   │
             └─────────┬─────────┘
                       ▼
                  Speech Layer
                       │
                       ▼
                  Existing TTS
                       │
                       ▼
                     Cache
                       │
                       ▼
                    Player
```

---

# 37. 成功标准

V2 第一阶段不以“功能数量”作为成功标准。

真正的成功标准是：

### 输入

一部长篇小说。

### 输出

相比 V1：

- 更少的未知说话人
- 更少的错误角色
- 更少的同一人物被拆成多个角色
- 更好的跨 Chunk 对话识别
- 更稳定的角色画像
- 更稳定的 Scene 判断
- 更连续的人物状态
- 更少的 LLM 无效输出

最终：

```text
角色识别准确率 ↑
上下文连续性 ↑
错误角色数量 ↓
Unknown Speaker ↓
LLM 无效输出 ↓
```

同时不能破坏：

```text
TTS
缓存
播放
UI
已有数据库
```

---

# 38. 开发总原则

## 原则 1

**先解决分析准确性，再增加高级智能。**

## 原则 2

**规则能解决的问题不要交给 LLM。**

## 原则 3

**LLM 输出必须结构化。**

## 原则 4

**LLM 输出不能未经验证直接进入数据库。**

## 原则 5

**Knowledge 不真正遗忘，只压缩 Context。**

## 原则 6

**Character 必须使用稳定 ID，而不是字符串作为核心身份。**

## 原则 7

**Scene 是人物和对话上下文的重要连接层。**

## 原则 8

**Chunk 是处理单位，Context 是推理环境，两者必须分离。**

## 原则 9

**V1 TTS Runtime 尽量保持稳定。**

## 原则 10

**所有分析结果都应该能够追溯到原始文本位置。**

---

# 39. 最终产品架构目标

xMOD-AAE V2 不只是：

```text
TXT → TTS
```

而是：

```text
              Novel
                │
                ▼
        Novel Intelligence
                │
      ┌─────────┼─────────┐
      ▼         ▼         ▼
 Character     Scene    Narrative
   System      System     State
      │         │         │
      └─────────┼─────────┘
                ▼
        Speaker Attribution
                │
                ▼
          Structured Data
                │
                ▼
          Speech Planning
                │
                ▼
             TTS Engine
                │
                ▼
              Player
```

其中 V2 最核心的变化是：

> **从“批量分析文本”转变为“沿小说阅读进度持续构建结构化 Narrative State”。**

这样才能从根本上改善长篇小说中的角色识别与说话人判断，并为后续更高质量的 AI 有声阅读打基础。

---

# 40. 当前开发优先级总表

| 优先级 | 功能 | 状态 |
|---|---|---|
| P0 | 语义切分 | V2 核心 |
| P0 | Chunk / Context 分离 | V2 核心 |
| P0 | Character ID + Alias | V2 核心 |
| P0 | Scene | V2 核心 |
| P0 | Narrative State | V2 核心 |
| P0 | Speaker Attribution | V2 核心 |
| P0 | Confidence | V2 核心 |
| P0 | Validation | V2 核心 |
| P0 | Memory Compression / Retrieval | V2 核心 |
| P1 | 局部重新分析 | V2 规划 |
| P1 | Analysis Version | V2 规划 |
| P2 | 自动二次分析 | 延后 |
| P2 | 高级 Narrative Intelligence | 延后 |
| P2 | 作者风格指纹 | 延后 |
| P3 | 更复杂世界观/因果图 | 延后 |

---

## 一句话开发目标

> **在不破坏现有 TTS、播放、缓存和 UI 基础的前提下，将 xMOD-AAE 的 V1“批量文本角色分析器”升级为一个具有语义切分、持续 Narrative State、稳定 Character ID、Scene 上下文、Speaker Attribution、Memory Retrieval 和结果 Validation 能力的长篇小说分析引擎。**
