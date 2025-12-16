# core 目录说明

职责：提供配置加载、LangGraph 编排、节点实现、API/DB 封装、日志与异常基础设施。

- `config.py`：读取/校验 `config.yaml`，暴露配置对象；新增配置需设默认值并校验类型。
- `graph.py`：LangGraph 主流程装配；节点放 `nodes/`；节点接口入参/出参保持可序列化。
- `nodes/`：业务节点与工具函数，遵循单一职责；避免直接依赖 UI/外部服务，需通过 API 封装层。
- `api/llm.py`：LLM/语音等外部模型调用统一入口，处理鉴权、重试、超时与日志。
- `database.py`：数据库接入与会话管理。
- `logging_setup.py`：`structlog` 配置；禁止裸 `print`。
- `exceptions.py`：集中定义语义化异常类型。

开发要点：
- 新节点/模块必须写简要 docstring，说明输入/输出/副作用。
- 关键路径记录结构化日志（字段使用 snake_case）。
- 与外部服务交互请通过封装层，避免在节点中散落请求逻辑。

