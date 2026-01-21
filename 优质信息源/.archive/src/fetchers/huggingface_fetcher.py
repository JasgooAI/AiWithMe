"""Hugging Face Papers 抓取器"""
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional

from fetchers.base import BaseFetcher, Article
from utils.logger import logger


class HuggingFaceFetcher(BaseFetcher):
    """Hugging Face Daily Papers 抓取器"""

    def fetch(self) -> list[Article]:
        """抓取 HF Daily Papers"""
        articles = []

        url = self.config.get('url', 'https://huggingface.co/papers')
        logger.info(f"[{self.source_id}] 正在抓取 HuggingFace Papers: {url}")

        html = self._get_page(url)
        if not html:
            return articles

        try:
            soup = BeautifulSoup(html, 'lxml')

            # HF Papers 页面结构
            paper_items = soup.select('article')
            limit = self.config.get('limit', 20)

            for item in paper_items[:limit]:
                article = self._parse_paper(item)
                if article:
                    articles.append(article)

            logger.info(f"[{self.source_id}] 抓取到 {len(articles)} 篇论文")

        except Exception as e:
            logger.error(f"[{self.source_id}] 抓取失败: {e}")

        return articles

    def _parse_paper(self, item) -> Optional[Article]:
        """解析单个论文"""
        try:
            # 获取标题和链接
            title_elem = item.select_one('h3 a')
            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            link = title_elem.get('href', '')

            if not link:
                return None

            # 完整链接
            if link.startswith('/'):
                url = f"https://huggingface.co{link}"
            else:
                url = link

            # 获取摘要
            summary = ""
            summary_elem = item.select_one('p')
            if summary_elem:
                summary = self._clean_text(summary_elem.get_text())
                summary = self._truncate_content(summary, 500)

            # 获取点赞数
            upvotes_elem = item.select_one('[class*="upvote"]')
            upvotes = ""
            if upvotes_elem:
                upvotes = upvotes_elem.get_text(strip=True)

            if upvotes:
                summary = f"Upvotes: {upvotes}\n{summary}"

            return Article(
                url=url,
                title=title,
                source_id=self.source_id,
                source_name=self.source_name,
                summary=summary,
            )

        except Exception as e:
            logger.error(f"[{self.source_id}] 解析论文失败: {e}")
            return None
