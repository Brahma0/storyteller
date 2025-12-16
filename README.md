## Cyber-Pingshu Workstation

桌面端赛博评书自动化工作站。核心技术栈：PySide6 + LangGraph + Playwright + FFmpeg。

- 业务设计与架构说明见 `docs/storyteller-design-v2.1.md`
- 本仓库当前为工程骨架，后续可按节点逐步补全实现。

### 目录结构

- `app.py`：PySide6 启动入口
- `config.yaml`：全局配置
- `core/`：核心业务与基础设施
- `ui/`：桌面 UI 代码
- `assets/`：静态资源（音效、轮播素材、字体等）
- `models/`：本地模型文件（可选）
- `output/`：产出物（脚本、音频、视频等）
- `logs/`：日志文件
- `checkpoints/`：LangGraph 状态检查点
- `db/`：SQLite 数据库
- `tests/`：测试代码

### 开发环境（推荐使用 uv）

```bash
# 安装依赖并创建虚拟环境
uv sync

# 如需语音相关可选依赖：
uv sync --group voice
```

### 运行

```bash
uv run python app.py
```

> 注意：本项目大量依赖外部服务（OpenRouter、图像/TTS/ASR API），需在 `config.yaml` 中配置逻辑参数，在 `.env` 中填写对应的 API Key，并确保本地安装 FFmpeg。

### 全局参数与环境变量约定

- **业务全局参数**：统一放在 `config.yaml` 中（模型路由、视频参数、路径、开关等），其中敏感值使用占位符 `${VAR_NAME}`。
- **私密参数 / 不同环境差异**：放在根目录 `.env`（基于 `.env.example` 拷贝），例如：

```env
OPENROUTER_API_KEY=your-openrouter-api-key
OPENAI_API_KEY=your-openai-api-key
ELEVENLABS_API_KEY=your-elevenlabs-api-key
```

- 启动时 `app.py` 会先加载 `.env`，再解析 `config.yaml`，`core/config.py` 会自动把 `${OPENROUTER_API_KEY}` 这类占位符展开为环境变量的实际值。
