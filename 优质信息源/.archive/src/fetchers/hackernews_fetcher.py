"""Hacker News 抓取器"""
import requests
from typing import Optional

from fetchers.base import BaseFetcher, Article
from utils.logger import logger


class HackerNewsFetcher(BaseFetcher):
    """Hacker News 抓取器，使用官方 API"""

    API_BASE = "https://hacker-news.firebaseio.com/v0"

    def fetch(self) -> list[Article]:
        """抓取 HN 热门文章"""
        articles = []

        logger.info(f"[{self.source_id}] 正在抓取 Hacker News")

        try:
            # 获取热门文章 ID 列表
            story_type = self.config.get('story_type', 'top')  # top, new, best
            response = requests.get(
                f"{self.API_BASE}/{story_type}stories.json",
                timeout=30
            )
            response.raise_for_status()
            story_ids = response.json()

            limit = self.config.get('limit', 30)
            min_score = self.config.get('min_score', 50)

            for story_id in story_ids[:limit * 2]:  # 多获取一些以过滤低分
                article = self._fetch_story(story_id, min_score)
                if article:
                    articles.append(article)
                    if len(articles) >= limit:
                        break

            logger.info(f"[{self.source_id}] 抓取到 {len(articles)} 篇文章")

        except Exception as e:
            logger.error(f"[{self.source_id}] 抓取失败: {e}")

        return articles

    def _fetch_story(self, story_id: int, min_score: int) -> Optional[Article]:
        """获取单个故事详情"""
        try:
            response = requests.get(
                f"{self.API_BASE}/item/{story_id}.json",
                timeout=10
            )
            response.raise_for_status()
            item = response.json()

            if not item or item.get('type') != 'story':
                return None

            score = item.get('score', 0)
            if score < min_score:
                return None

            url = item.get('url', '')
            if not url:
                # Ask HN 等没有外部链接的帖子
                url = f"https://news.ycombinator.com/item?id={story_id}"

            title = item.get('title', 'Untitled')
            comments = item.get('descendants', 0)

            summary = f"Score: {score} | Comments: {comments}"

            return Article(
                url=url,
                title=title,
                source_id=self.source_id,
                source_name=self.source_name,
                summary=summary,
                author=item.get('by'),
            )

        except Exception as e:
            logger.debug(f"[{self.source_id}] 获取故事 {story_id} 失败: {e}")
            return None
