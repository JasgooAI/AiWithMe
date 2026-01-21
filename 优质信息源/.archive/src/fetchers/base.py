"""抓取器基类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import requests

from utils.logger import logger


@dataclass
class Article:
    """文章数据类"""
    url: str
    title: str
    source_id: str
    source_name: str
    content: str = ""
    summary: str = ""
    published_at: Optional[str] = None
    author: Optional[str] = None

    # AI 处理后填充
    title_zh: Optional[str] = None
    keywords: Optional[str] = None
    category: Optional[str] = None
    ai_summary: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'url': self.url,
            'title': self.title,
            'title_zh': self.title_zh,
            'source_id': self.source_id,
            'source_name': self.source_name,
            'content': self.content,
            'summary': self.ai_summary or self.summary,
            'keywords': self.keywords,
            'category': self.category,
            'published_at': self.published_at,
            'author': self.author,
        }


class BaseFetcher(ABC):
    """抓取器基类"""

    def __init__(self, source_config: dict):
        self.config = source_config
        self.source_id = source_config['id']
        self.source_name = source_config.get('name', self.source_id)
        self.url = source_config.get('url', '')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    @abstractmethod
    def fetch(self) -> list[Article]:
        """抓取文章，子类必须实现"""
        pass

    def _get_page(self, url: str, timeout: int = 30) -> Optional[str]:
        """获取网页内容"""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response.text
        except requests.RequestException as e:
            logger.error(f"[{self.source_id}] 获取页面失败 {url}: {e}")
            return None

    def _truncate_content(self, content: str, max_length: int = 5000) -> str:
        """截断内容到指定长度"""
        if len(content) <= max_length:
            return content
        return content[:max_length] + "..."

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""
        # 移除多余空白
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]
        return '\n'.join(lines)
