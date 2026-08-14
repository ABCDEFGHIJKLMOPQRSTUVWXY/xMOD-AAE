# xMOD-AAE 模块摘要

> 完整版见 `docs/MODULES.md`。

## 项目定位
AI 有声阅读引擎（Windows/macOS）：txt 导入 → 角色识别 → 音色匹配 → TTS 合成 → 逐句播放；支持本地（Ollama + Edge TTS）与云端（OpenAI 兼容 API + MiMo TTS）双后端。

## 分层结构
| 层 | 模块 | 职责 |
|---|---|---|
| 基础设施 | `main.py` `config.py` `secret_store.py` | 入口；路径配置；API 密钥经 keyring/文件安全存储 |
| 文本处理 | `text_processor/` | 编码探测→章节切分→对话/旁白分段（引号+冒号识别） |
| 角色引擎 | `character_engine/` | LLM 识别说话人→称呼归一→台词聚合→角色画像→音色分配→SQLite 持久化 |
| 语音合成 | `tts_engine/` | TTSDriver 驱动体系（Edge TTS / MiMo）、分块构建、ffmpeg 转码、音频缓存 |
| 播放层 | `player/` | 后台合成预加载队列(QThread)、pygame 播放、播放控制状态机 |
| 界面层 | `ui/` | 主窗口编排、书架、章节目录、阅读视图高亮、控制条、角色面板、设置对话框 |

## 核心要点
- **驱动可插拔**：TTS 抽象为 `TTSDriver` + `DriverManager`，缓存键含 driver/voice_params 防串音
- **严格路由**：LLM 后端按 `llm_mode` 设置路由（ollama/cloud），未配置时报错而非静默产「未知」角色
- **批量控制**：说话人识别按 ≤5 段且 ≤6000 字符分批，防云端超时
- **健壮降级**：ffmpeg 缺失保 WAV、LLM 输出非法自纠错一次、解析失败回退默认画像
- **幂等迁移**：SQLite 加列守卫式升级，旧库无需删表
- **测试**：pytest 覆盖核心逻辑，运行 `python -m pytest tests/`
