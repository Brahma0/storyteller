import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from dotenv import load_dotenv

from core.config import load_config
from core.logging_setup import setup_logging
from ui.main_window import MainWindow


BASE_DIR = Path(__file__).resolve().parent


def main() -> None:
    """PySide6 桌面应用入口。"""
    # 先加载 .env / 环境变量，再解析 config.yaml 中的 ${VAR} 占位符
    load_dotenv(BASE_DIR / ".env")

    config = load_config(BASE_DIR / "config.yaml")
    setup_logging(config)

    app = QApplication(sys.argv)
    window = MainWindow(config=config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":  # pragma: no cover
    main()
