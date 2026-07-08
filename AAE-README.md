
AI Audiobook Engine 开发指南（V1.0）

1. 项目定位
   项目名称（建议）

AI Audiobook Engine（AAE）

定位：

一个面向电子书阅读器的 AI 有声阅读引擎。

它不是阅读器，而是阅读器的 AI 能力平台。

首个 Adapter 为 legado-E。

未来可以支持：

Windows 阅读器
Android 阅读器
Web 阅读器
iOS 阅读器
Kindle（理论上）
浏览器插件

因此整个系统必须保持平台无关。

2. 设计目标

本项目需要满足以下目标：

AI能力
AI角色识别
旁白识别
多角色语音
Voice Mapping
情感扩展（后期）
播放能力

支持：

普通TTS
Streaming TTS
Batch TTS
Hybrid TTS
Provider

同时支持：

本地模型
云端API
PC Server

Provider 可以自由切换。

开源生态

支持：

Plugin
Adapter
Community Voice
Community Provider

任何人都可以增加新的 Provider。

3. 总体架构
   Reader (Legado-E)

   │

   ▼

AI SDK（Bridge）

    │

    ▼

Android AI Service

    │

    ▼

AI Engine Core

    │

 ┌──────┴────────┐
 │               │
 ▼               ▼

Cloud Provider   Local Provider

    │

    ▼

Audio Engine

    │

    ▼

AudioTrack

整个项目采用：

Adapter + Engine + Provider

模式。

4. Repository 规划（Monorepo）

建议采用 Monorepo。

ai-audiobook-engine/

apps/
    legado-adapter/
    android-demo/
    desktop-server/

sdk/
    android-sdk/

engine/
    core/
    nlp/
    tts/
    scheduler/
    cache/
    audio/
    voice/
    provider/

providers/
    piper/
    coqui/
    azure/
    elevenlabs/
    openai/
    custom/

docs/

examples/

tools/

这样以后增加 Provider 不需要修改 Engine。

5. 模块设计
   SDK（Bridge）

SDK 是整个项目最重要的接口层。

负责：

与阅读器通信
接收阅读事件
控制播放
不参与 AI 推理

接口示例：

start()

pause()

resume()

stop()

seek()

setVoice()

enableCharacterVoice()

downloadChapter()

SDK 不依赖任何 Provider。

Android AI Service

采用：

Foreground Service

负责：

Buffer
Queue
Scheduler
Cache
Playback

它是整个 Android 端的大脑。

AI Engine

Engine 只负责 AI。

不负责 UI。

建议拆分：

core/

nlp/

tts/

voice/

provider/

scheduler/

cache/

audio/

download/
6. NLP Engine

职责：

把小说转换成：

Speaker Timeline

例如：

Narrator

A

B

Narrator

A

C

输出：

speaker

type

text

推荐流程：

规则切分

↓

LLM角色识别

↓

Memory

↓

JSON
LLM推荐路线

第一阶段：

规则 + LLM

第二阶段：

Role Memory

第三阶段：

Entity Tracking

第四阶段：

Emotion

推荐：

DeepSeek
或其他兼容 OpenAI API 的模型服务
7. TTS Engine

采用双引擎。

Batch

负责：

整章
后台生成
高质量
Stream

负责：

当前句子
实时响应

最终采用：

Hybrid。

8. Voice Engine

维护：

角色

↓

Voice

例如：

Narrator

↓

voice_narrator

A

↓

voice_female_01

B

↓

voice_male_03

以后支持：

Voice Pack。

9. Provider

Provider 必须插件化。

统一接口。

例如：

synthesize()

stream()

voices()

download()

train()

Provider 包括：

本地：

Piper TTS
Coqui TTS

云：

OpenAI
Azure
ElevenLabs

以后增加 Provider：

无需修改 Engine。

10. Scheduler

整个系统最重要。

负责：

什么时候：

生成

缓存

播放

删除

下载

切 Provider

全部由 Scheduler 决定。

不要把逻辑写进 Player。

11. Audio Engine

负责：

PCM

↓

Opus

↓

Player

建议：

AudioTrack。

播放器不关心：

Provider。

播放器只播放 Audio Chunk。

12. Cache

建议：

SQLite

文件缓存。

数据库：

保存：

Book

Chapter

Chunk

Metadata

文件：

保存：

Audio

13. PC AI Server

PC 负责：

训练

Batch

Streaming

Voice Clone

Android：

只负责：

播放。

PC Server 可以以后增加。

不是 MVP。

14. Hybrid TTS

采用：

Streaming

Batch

同时运行。

策略：

播放：

当前内容

后台：

持续生成未来内容。

网络异常：

自动切本地。

云失败：

自动切 Provider。

15. 推荐开发顺序（Roadmap）
    Milestone 1：基础框架

目标：

SDK
Android AI Service
Provider Interface
Demo 播放

验收标准：

能够从阅读器获取文本。
能够通过统一接口请求语音（可先返回模拟音频）。
Android 后台服务能够控制播放。
Milestone 2：本地 TTS

接入：

Piper TTS

完成：

普通朗读。

验收标准：

本地 TXT/EPUB 能连续朗读。
支持暂停、继续、跳章。
Milestone 3：NLP

加入：

LLM
Speaker Timeline

完成：

角色识别。

验收标准：

能正确区分旁白与对话。
能为主要角色分配稳定的角色 ID。
Milestone 4：Voice Mapping

完成：

不同角色。

不同声音。

验收标准：

同一角色保持固定音色。
支持用户手动修改角色与音色绑定。
Milestone 5：Cloud Provider

增加：

Azure

OpenAI

ElevenLabs

完成：

Provider 插件。

验收标准：

可自由切换本地/云 Provider。
Provider 故障自动回退。
Milestone 6：Desktop AI Server

完成：

Batch

Streaming

Hybrid

训练。

验收标准：

PC 能批量生成章节音频。
Android 可流式接收或同步预生成内容。
Milestone 7：Plugin Ecosystem

支持：

Community Provider

Community Voice

Community Adapter

建立：

Plugin API。

验收标准：

第三方无需修改核心即可新增 Provider 或 Adapter。
16. MVP 范围（建议）

为了尽快验证产品价值，我建议 MVP 不要一开始就做所有功能，而是聚焦于：

使用 legado-E 作为阅读入口。
支持本地 TTS（Piper）。
使用 LLM 做基础角色识别。
提供旁白 + 两个角色的多音色朗读。
完成角色映射界面。
支持章节级预生成和缓存。

这样大约可以覆盖 80% 的核心体验，同时保持开发复杂度可控。

最后的建议

我建议把这个项目定位为：

一个可扩展的 AI Audiobook Engine，而不是某个阅读器的插件。

这样阅读器只是一个 Adapter，AI 引擎才是核心资产。未来无论接入新的阅读器、增加新的 TTS 服务、切换新的 LLM，甚至增加视频字幕朗读、漫画配音等能力，都不需要推翻整体架构，只需新增适配器或 Provider 即可。这样的架构更适合长期维护，也更符合开源项目的发展模式。
