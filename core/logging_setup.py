from __future__ import annotations

import logging
from logging import Logger
from pathlib import Path

import structlog

from .config import AppConfig


def setup_logging(config: AppConfig) -> Logger:
    """配置标准 logging 与 structlog，输出到控制台与日志文件。"""
    log_dir = config.paths.logs
    log_dir.mkdir(parents=True, exist_ok=True)

    log_level = getattr(logging, config.logging.level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.EventRenamer("message"),
            structlog.processors.JSONRenderer() if config.logging.format == "json" else structlog.processors.KeyValueRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    logger = structlog.get_logger("cyber_pingshu")
    logger.info("logging_initialised", level=config.logging.level, format=config.logging.format)
    return logger
