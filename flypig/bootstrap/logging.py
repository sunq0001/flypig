"""Loguru 日志初始化

为什么做：开发和生产环境需要一致的日志格式和级别控制，print 无法满足文件轮转、异步写入、彩色输出等需求。

实现方法：Loguru 一行初始化，配置格式/级别/文件轮转/异步写入/彩色终端输出，替代 stdlib logging。

实现效果：日志统一可搜索，支持运行时动态调整日志级别，错误定位快。

技术栈：loguru (file rotation, async write, colorized output)

层&依赖：core 层，不依赖其他业务模块，仅被其他模块 import 使用
细节见文档：docs/docs_refactor/tech-stack.md → §日志系统、resilience.md → §日志系统
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def init_logging(log_dir: str | Path | None = None, level: str = "DEBUG") -> None:
    """初始化 Loguru 全局日志配置

    Args:
        log_dir: 日志文件输出目录，默认 ~/.flypig/logs
        level: 日志级别，默认 DEBUG
    """
    if log_dir is None:
        log_dir = Path.home() / ".flypig" / "logs"
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # 移除默认 handler
    logger.remove()

    # 终端彩色输出
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:7}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # 文件日志（带轮转：10MB / 保留 30 天）
    logger.add(
        str(log_dir / "flypig_{time:YYYY-MM-DD}.log"),
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:7} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="30 days",
        compression="gz",
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
    )

    logger.info("日志初始化完成: level={}, dir={}", level, log_dir)
