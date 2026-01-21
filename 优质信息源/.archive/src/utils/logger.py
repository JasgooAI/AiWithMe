"""日志配置模块"""
import logging
import sys
from datetime import datetime
from pathlib import Path

from .config import config


def setup_logger(name: str = 'intel_collector') -> logging.Logger:
    """设置并返回日志记录器"""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # 确保日志目录存在
    config.logs_path.mkdir(parents=True, exist_ok=True)

    # 文件处理器 - 按日期命名
    log_file = config.logs_path / f'{datetime.now().strftime("%Y-%m-%d")}.log'
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# 全局日志实例
logger = setup_logger()
