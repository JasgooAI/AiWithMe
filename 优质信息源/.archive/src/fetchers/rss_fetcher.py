"""RSS/Atom 抓取器"""
import feedparser
from datetime import datetime
from typing import Optional

from fetchers.base import BaseFetcher, Article
from utils.logger import logger


class RSSFetcher(BaseFetcher):
    """RSS/Atom Feed 抓取器"""

    def fetch(self) -> list[Article]:
        """抓取 RSS Feed"""
        articles = []
        feed_url = self.config.get('feed_url') or self.url

        logger.info(f"[{self.source_id}] 正在抓取 RSS: {feed_url}")

        try:
            feed = feedparser.parse(feed_url, agent=self.headers['User-Agent'])

            if feed.bozo and not feed.entries:
                logger.error(f"[{self.source_id}] RSS 解析失败: {feed.bozo_exception}")
                return articles

            limit = self.config.get('limit', 20)

            for entry in feed.entries[:limit]:
                article = self._parse_entry(entry)
                if article:
                    articles.append(article)

            logger.info(f"[{self.source_id}] 抓取到 {len(articles)} 篇文章")

        except Exception as e:
            logger.error(f"[{self.source_id}] 抓取失败: {e}")

        return articles

    def _parse_entry(self, entry) -> Optional[Article]:
        """解析单个 RSS 条目"""
        try:
            url = entry.get('link', '')
            if not url:
                return None

            title = entry.get('title', 'Untitled')

            # 获取内容
            content = ""
            if entry.get('content'):
                content = entry.content[0].get('value', '')
            elif entry.get('summary'):
                content = entry.summary
            elif entry.get('description'):
                content = entry.description

            # 清理 HTML 标签获取纯文本摘要
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'lxml')
            summary = self._clean_text(soup.get_text())
            summary = self._truncate_content(summary, 1000)

            # 解析发布时间
            published = None
            if entry.get('published_parsed'):
                try:
                    published = datetime(*entry.published_parsed[:6]).isoformat()
                except:
                    pass
            elif entry.get('updated_parsed'):
                try:
                    published = datetime(*entry.updated_parsed[:6]).isoformat()
                except:
                    pass

            return Article(
                url=url,
                title=title,
                source_id=self.source_id,
                source_name=self.source_name,
                content=self._truncate_content(content, 5000),
                summary=summary,
                published_at=published,
                author=entry.get('author'),
            )

        except Exception as e:
            logger.error(f"[{self.source_id}] 解析条目失败: {e}")
            return None
