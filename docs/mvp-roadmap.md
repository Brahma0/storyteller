## Cyber-Pingshu Workstation – MVP 迭代规划（v1 输入：至少一个数据源爬取）

> 说明：本规划以 `storyteller-design-v2.1.md` 与 `storyteller-review.md` 为基础，MVP 即 Phase 1（核心功能验证）：**从至少 1 个外部数据源爬取热点 → 评书脚本生成 → TTS 音频合成 → 基础视频合成 → 本地预览与手动发布**。

---

## 里程碑概览

- **M0 – 基础设施就绪**：配置、日志、LangGraph、DB、基础 UI 骨架可运行。
- **M1 – 单源雷达 + 手动选题 → 一条龙生成**：至少 1 个数据源（建议知乎科技榜）打通「爬取 → 选题 → 脚本 → TTS → 视频 → 本地预览」。
- **M2 – 进度可视化 + 轻量审核 + 错误处理**：用户能看到每个任务的进度与错误提示，脚本有基础合规检查。
- **M3 – 工程收尾（性能/成本基础控制）**：补齐必要的配置、日志和简单成本控制，形成可长期演进的 MVP 基线。

---

## M0 – 基础设施与骨架（Iteration 0）

- **配置与环境**
  - 在 `config.yaml` + `.env` 中补齐必需字段（API Key、路径、基础模型路由），由 `core/config.py` 统一加载与校验。
  - 明确本地目录：`assets/`、`output/`、`logs/`、`db/`、`checkpoints/`、`models/`（参考评审文档建议）。

- **日志与监控基础**
  - 完成 `core/logging_setup.py`：使用 `structlog` + 分级日志（INFO/ERROR）。
  - 所有核心节点与外部调用写日志到 `logs/storyteller.log`，按任务 ID 打标签。

- **LangGraph 初版状态机**
  - 在 `core/graph.py` 定义最小 `AgentState`：
    - 核心数据：`topic`, `script`, `audio_path`, `video_path`.
    - 控制字段：`task_id`, `current_node`, `progress`, `error_message?`.
  - 实现最简单的“假流程”图：`Start -> DummyLLMNode -> DummyRenderNode -> End`，用于验证状态流转与 UI 通知。

- **数据库初始化**
  - 使用 SQLite 创建基础表（参考评审意见）：
    - `topics`：`id`, `source`, `source_url`, `title`, `score_ai`, `status`, `created_at`.
    - `productions`：`id`, `topic_id`, `script_content`, `video_path`, `status`, `created_at`.

- **UI 骨架**
  - 在 `ui/main_window.py` 中实现：
    - 主窗口 + 菜单（设置、日志查看、关于）。
    - 简单任务列表区（仅展示 task_id 与状态）。
    - 一个“启动空任务”按钮，用于测试与 LangGraph 的对接。

---

## M1 – 单源雷达 + 一条龙生产链路（Iteration 1）

> 目标：完成 Phase 1 v1 要求：**至少一个数据源的基础爬取** + 评书化脚本 + TTS + 基础视频合成 + 本地预览。发布阶段采用**手动上传**。

- **A. 单源全网雷达（建议知乎科技榜）**
  - 新建 `core/spider/zhihu.py`（或类似模块）：
    - 使用 Playwright 抓取知乎科技榜标题 + 链接。
    - 控制频率：例如「手动触发」+ 内部冷却时间（如 30 分钟），避免成为后台轮询。
  - 将爬取结果落库到 `topics` 表，字段包括：`title`, `source_url`, `source='zhihu'`, `created_at`。
  - 简单评分策略（可先不做三 Agent）：
    - 规则打分：如标题长度、关键字命中等。
    - 将 `score_ai` 字段填入一个 0–10 的启发式分数。

- **B. UI：雷达面板与选题**
  - 在主窗口中新增「雷达」页签：
    - 显示来自 `topics` 表的最新 N 条候选，按 `score_ai` / `created_at` 排序。
    - 支持勾选一个或多个 topic，点击「生成评书视频」发起任务。

- **C. 评书脚本生成（Writer Node）**
  - 在 `core/api/llm.py` 中封装文本 LLM 调用（基于 OpenRouter / OpenAI 风格 API）：
    - 提供：`generate_ping_shu_script(topic: str, config: Config) -> str`.
  - Prompt 设计遵循 v2.1 文档：
    - 角色：赛博说书人·零号先生。
    - 结构：定场诗 → 开场白 → 正文（三翻四抖） → 结尾留扣子 → [下回分解]。
    - 术语转译表：服务器→藏经阁、Bug→走火入魔、程序员→符文师等。
  - 将生成脚本写入 `AgentState.script` 并同时持久化到 `productions.script_content`。

- **D. TTS 音频合成（TTS Node – 云优先）**
  - 在 `core/audio/tts.py` 中封装简单 TTS：
    - 优先接入一个云 TTS（如 OpenAI TTS / ElevenLabs），统一接口：`synthesize(script) -> audio_path`.
    - 暂不实现复杂情感控制，只保证音色与清晰度可用。
  - 输出文件放到 `output/{task_id}/audio.wav`，路径写入 `AgentState.audio_path`。

- **E. 基础视频合成（Render Node – 极简版）**
  - 在 `core/video/render.py` 中，使用 FFmpeg 完成基础合成：
    - 时间轴以音频时长为主线。
    - 使用 `assets/carousel/` 下固定若干循环素材拼接/循环，保证覆盖全时长。
    - 暂不实现 Ken Burns / 特写图，只做最简单的「背景 + 音频」竖屏视频。
  - 输出到 `output/{task_id}/final.mp4`，路径写入 `AgentState.video_path` 和 `productions.video_path`。

- **F. 预览与结果管理**
  - UI 在任务完成后：
    - 在任务列表中标记任务状态为「完成」。
    - 提供按钮「打开产出目录」或「在系统播放器中打开视频」。
  - 在 `productions` 表记录 `status='completed'` 及 `created_at`。

---

## M2 – 进度可视化 + 轻量审核 + 错误处理（Iteration 2）

- **A. 进度与状态字段完善**
  - 扩展 `AgentState` 与数据库：
    - 字段：`current_node`, `progress (0-100)`, `error_message?`.
  - 在 LangGraph 中，每个 Node 完成后更新 `current_node` 和 `progress`。
  - UI 中：
    - 每个任务显示当前节点（如「脚本生成中」「TTS 合成中」「视频渲染中」）。
    - 使用简单进度条（近似分配各节点权重即可）。

- **B. 轻量级内容审核（文本层）**
  - 在 Writer Node 与 TTS Node 之间增加 `Audit Node`：
    - 使用本地敏感词表（文本文件或 `sensitive_words` 表）对脚本进行关键词匹配。
    - 审核不过：将状态更新为 `status='rejected'`，在 UI 中突出提示。
  - 审核逻辑保持简洁，后续再接入语义审核 API。

- **C. 错误处理与重试（最小版本）**
  - 为 LLM/TTS/FFmpeg 调用增加 try/except：
    - 失败时写入 `error_message`，状态更新为 `status='failed'`。
    - 简单一次重试机制（例如间隔几秒重试 1 次）。
  - UI 中提供“重新开始本任务”的入口（清理旧产出后重新提交）。

---

## M3 – 工程收尾与成本/配置基础（Iteration 3）

- **A. 配置整理与环境切换**
  - 将模型路由、TTS 选择、是否启用审核等开关，集中在 `config.yaml`：
    - 如：`llm.provider`, `tts.provider`, `audit.enabled`, `spider.zhihu.enabled`.
  - 支持简单的「开发/生产」模式切换（例如通过环境变量指定配置 profile）。

- **B. 简单成本与调用控制**
  - 在配置中增加软限制字段：
    - `daily_llm_budget`、`daily_tts_budget` 或调用次数上限。
  - 每次调用前估算一次消费（粗略即可），如超过当日限额则：
    - 在 UI 弹出确认提示，允许用户手动继续或放弃。

- **C. 文档与测试**
  - 在 `README.md` 中补充：
    - 如何配置单源雷达、如何运行完整 MVP 流程。
  - 在 `tests/` 下为关键模块增加最小单元测试：
    - 配置加载、数据库读写、LLM 包装器的入参与返回结构校验等。

---

## 出版标准（MVP 完成判定）

当满足以下条件时，可视为 MVP 版本达成：

- 用户在桌面端可以：
  - 通过「雷达」面板，从**至少一个外部数据源**中选择热点选题；
  - 一键发起任务，看到清晰的任务进度与当前步骤；
  - 获取一条完整的评书风格视频（音频+背景视频），并在本地预览；
  - 在脚本层面通过基础敏感词审核，避免明显违规内容。
- 工程角度：
  - 所有核心流程都有结构化日志；
  - 关键出错路径有友好的 UI 提示，不会无声失败；
  - 主要行为由 `config.yaml` 可配置，方便后续 Phase 2/3 的自动化与扩展。


