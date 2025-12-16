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
from core.database import Database
from core.spider.zhihu import fetch_zhihu_hot_topics
from core.spider.hackernews import fetch_hn_topics


class MainWindow(QMainWindow):
    """主窗口：展示选题列表、任务进度与视频预览占位。"""

    def __init__(self, config: AppConfig, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._db = db
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
        """刷新选题列表。

        流程：
        1. 先尝试从知乎抓取最新热点并写入 topics 表（失败不会中断）。
        2. 若知乎被 403/反爬挡住，则继续尝试从 Hacker News 抓取。
        3. 再从本地 SQLite `topics` 表读取最新记录；
        4. 若当前尚无数据，则回退到示例占位数据。
        """
        self.topic_list.clear()

        total_inserted = 0

        # Step 1: 抓取知乎热点落库（忽略异常，避免影响本地体验）
        try:
            inserted = fetch_zhihu_hot_topics(self._db, limit=20)
            if inserted:
                total_inserted += inserted
                self._append_log(f"已从知乎抓取 {inserted} 条新热点。")
        except Exception as exc:  # pragma: no cover - 网络/解析异常兜底
            self._append_log(f"抓取知乎热点失败：{exc}")

        # Step 2: 如知乎无新增，则尝试从 Hacker News 抓取
        if total_inserted == 0:
            try:
                inserted_hn = fetch_hn_topics(self._db, limit=20)
                if inserted_hn:
                    total_inserted += inserted_hn
                    self._append_log(f"已从 Hacker News 抓取 {inserted_hn} 条新热点。")
            except Exception as exc:  # pragma: no cover
                self._append_log(f"抓取 Hacker News 热点失败：{exc}")

        # Step 3: 从本地 DB 读取最新选题
        try:
            rows = list(
                self._db.query(
                    "SELECT id, title, score_ai FROM topics ORDER BY created_at DESC LIMIT 50"
                )
            )
        except Exception as exc:  # pragma: no cover - UI 入口简单兜底
            self._append_log(f"读取数据库选题失败：{exc}")
            rows = []

        if rows:
            for row in rows:
                title = row["title"]
                score = row["score_ai"]
                display = f"{title}（评分：{score:.1f}）" if score is not None else title
                item = QListWidgetItem(display)
                # 在 UserRole 中存储 topic_id，后续任务触发可用
                item.setData(Qt.UserRole, row["id"])
                self.topic_list.addItem(item)
            self._append_log(f"已从数据库加载 {len(rows)} 条选题。")
        else:
            # 回退：仍提供占位示例，方便在未接入爬虫前体验 UI
            for idx in range(1, 6):
                item = QListWidgetItem(f"示例选题 {idx}")
                self.topic_list.addItem(item)
            self._append_log("当前数据库中暂无选题，已加载示例选题列表。")

    def _on_start_clicked(self) -> None:
        current = self.topic_list.currentItem()
        if current is None:
            self._append_log("请先选择一个选题。")
            return
        topic = current.text()
        topic_id = current.data(Qt.UserRole)
        if topic_id is not None:
            self._append_log(f"开始处理选题（ID={topic_id}）：{topic}")
        else:
            self._append_log(f"开始处理示例选题：{topic}")
        # 这里后续接入 LangGraph 工作流的触发

    def _append_log(self, text: str) -> None:
        self.log_view.append(text)
