from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.config import AppConfig


class MainWindow(QMainWindow):
    """主窗口：展示选题列表、任务进度与视频预览占位。"""

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("Cyber-Pingshu Workstation")
        self.resize(1280, 800)
        self._init_ui()

    def _init_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)

        # 左侧：选题列表
        left_panel = QVBoxLayout()
        lbl_topics = QLabel("选题列表")
        self.topic_list = QListWidget()
        self.btn_refresh_topics = QPushButton("刷新选题")
        left_panel.addWidget(lbl_topics)
        left_panel.addWidget(self.topic_list, 1)
        left_panel.addWidget(self.btn_refresh_topics)

        # 中间：日志/进度
        middle_panel = QVBoxLayout()
        lbl_log = QLabel("任务日志 / 状态")
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.btn_start = QPushButton("开始铸造")
        middle_panel.addWidget(lbl_log)
        middle_panel.addWidget(self.log_view, 1)
        middle_panel.addWidget(self.btn_start)

        # 右侧：预览占位
        right_panel = QVBoxLayout()
        lbl_preview = QLabel("视频预览 (占位)")
        lbl_preview.setAlignment(Qt.AlignCenter)
        self.preview_placeholder = QLabel("预览区域")
        self.preview_placeholder.setAlignment(Qt.AlignCenter)
        right_panel.addWidget(lbl_preview)
        right_panel.addWidget(self.preview_placeholder, 1)

        root_layout.addLayout(left_panel, 2)
        root_layout.addLayout(middle_panel, 3)
        root_layout.addLayout(right_panel, 3)

        # 事件绑定（占位，后续可接 LangGraph 任务触发）
        self.btn_refresh_topics.clicked.connect(self._on_refresh_topics)  # type: ignore[arg-type]
        self.btn_start.clicked.connect(self._on_start_clicked)  # type: ignore[arg-type]

    # --- slots -------------------------------------------------------------

    def _on_refresh_topics(self) -> None:
        # 目前先用占位数据，后续接入数据库/爬虫
        self.topic_list.clear()
        for idx in range(1, 6):
            item = QListWidgetItem(f"示例选题 {idx}")
            self.topic_list.addItem(item)
        self._append_log("已刷新示例选题。")

    def _on_start_clicked(self) -> None:
        current = self.topic_list.currentItem()
        if current is None:
            self._append_log("请先选择一个选题。")
            return
        topic = current.text()
        self._append_log(f"开始处理选题：{topic}")
        # 这里后续接入 LangGraph 工作流的触发

    def _append_log(self, text: str) -> None:
        self.log_view.append(text)
