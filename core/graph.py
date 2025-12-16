from __future__ import annotations

"""LangGraph 工作流骨架。

这里只定义状态类型与占位节点，供后续按设计文档逐步完善。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentState:
    # 核心数据
    topic: str = ""
    script: str = ""
    segments: List[Dict[str, Any]] = field(default_factory=list)
    video_path: str = ""
    audio_path: str = ""
    cover_path: str = ""

    # 控制流
    audit_result: bool = False
    retry_count: int = 0
    current_node: str = ""
    error_message: Optional[str] = None
    user_feedback: Optional[str] = None

    # 进度与元数据
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 持久化
    task_id: str = ""
    checkpoint_path: Optional[str] = None
    status: str = "pending"  # pending/running/completed/failed/cancelled


# 此处预留 LangGraph 构建函数（避免在骨架阶段强依赖具体库版本）

def build_workflow() -> Any:  # type: ignore[override]
    """返回工作流图对象的占位函数。

    实际实现中应使用 langgraph 的 Graph/StateGraph API 构建 Selector/Writer/Auditor/
    Visual/Render/HumanCheck/Publisher/Feedback/ErrorHandler 等节点。
    """

    raise NotImplementedError("LangGraph workflow construction is not implemented yet.")
