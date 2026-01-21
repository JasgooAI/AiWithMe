"""系统通知模块（跨平台支持）"""
import subprocess
import sys
from utils.logger import logger


def notify(title: str, message: str, sound: bool = True) -> None:
    """发送系统通知（自动检测平台）"""
    if sys.platform == 'darwin':
        _notify_macos(title, message, sound)
    elif sys.platform == 'linux':
        _notify_linux(title, message)
    elif sys.platform == 'win32':
        _notify_windows(title, message)
    else:
        logger.info(f"[通知] {title}: {message}")


def _notify_macos(title: str, message: str, sound: bool = True) -> None:
    """macOS 通知"""
    try:
        script = f'display notification "{message}" with title "{title}"'
        if sound:
            script += ' sound name "default"'

        subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True
        )
        logger.debug(f"通知已发送: {title} - {message}")
    except Exception as e:
        logger.debug(f"macOS 通知失败: {e}")


def _notify_linux(title: str, message: str) -> None:
    """Linux 通知（需要 notify-send）"""
    try:
        subprocess.run(
            ['notify-send', title, message],
            capture_output=True,
            text=True
        )
        logger.debug(f"通知已发送: {title} - {message}")
    except FileNotFoundError:
        logger.debug("notify-send 未安装，跳过通知")
    except Exception as e:
        logger.debug(f"Linux 通知失败: {e}")


def _notify_windows(title: str, message: str) -> None:
    """Windows 通知（需要 win10toast 或 plyer）"""
    try:
        # 尝试使用 plyer
        from plyer import notification
        notification.notify(title=title, message=message, timeout=5)
        logger.debug(f"通知已发送: {title} - {message}")
    except ImportError:
        logger.debug("plyer 未安装，跳过 Windows 通知")
    except Exception as e:
        logger.debug(f"Windows 通知失败: {e}")


def notify_completion(new_count: int, total_count: int) -> None:
    """发送收集完成通知"""
    if new_count > 0:
        notify(
            "情报收集完成",
            f"新增 {new_count} 篇文章，共处理 {total_count} 个来源"
        )
    else:
        notify(
            "情报收集完成",
            f"暂无新文章，共检查 {total_count} 个来源"
        )


def notify_error(error_msg: str) -> None:
    """发送错误通知"""
    notify("情报收集错误", error_msg, sound=True)
