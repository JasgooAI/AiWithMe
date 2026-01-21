"""网页抓取器"""
import subprocess
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Optional

from fetchers.base import BaseFetcher, Article
from utils.logger import logger


class WebpageFetcher(BaseFetcher):
    """网页抓取器，使用 CSS 选择器"""

    def fetch(self) -> list[Article]:
        """抓取网页文章列表"""
        articles = []

        logger.info(f"[{self.source_id}] 正在抓取网页: {self.url}")

        # 优先使用 curl（更可靠）
        html = self._get_page_with_curl(self.url)
        if not html:
            html = self._get_page(self.url)

        if not html:
            return articles

        try:
            soup = BeautifulSoup(html, 'lxml')

            # 获取配置的选择器
            selectors = self.config.get('selectors', {})
            item_selector = selectors.get('item', 'article')
            title_selector = selectors.get('title', 'h2 a, h3 a')
            link_selector = selectors.get('link', 'a')
            summary_selector = selectors.get('summary', 'p')

            items = soup.select(item_selector)
            limit = self.config.get('limit', 20)

            for item in items[:limit]:
                article = self._parse_item(item, title_selector, link_selector, summary_selector)
                if article:
                    articles.append(article)

            logger.info(f"[{self.source_id}] 抓取到 {len(articles)} 篇文章")

        except Exception as e:
            logger.error(f"[{self.source_id}] 抓取失败: {e}")

        return articles

    def _get_page_with_curl(self, url: str, timeout: int = 30) -> Optional[str]:
        """使用 curl 获取页面内容"""
        try:
            result = subprocess.run(
                ['curl', '-s', '-L', '--max-time', str(timeout),
                 '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                 '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                 url],
                capture_output=True,
                text=True,
                timeout=timeout + 5
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout
        except Exception as e:
            logger.debug(f"[{self.source_id}] curl 获取失败: {e}")
        return None

    def _parse_item(self, item, title_selector: str, link_selector: str, summary_selector: str) -> Optional[Article]:
        """解析单个文章项"""
        try:
            # 获取标题和链接
            title_elem = item.select_one(title_selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                link = title_elem.get('href', '')
            else:
                link_elem = item.select_one(link_selector)
                if not link_elem:
                    return None
                title = link_elem.get_text(strip=True) or 'Untitled'
                link = link_elem.get('href', '')

            if not link:
                return None

            # 处理相对链接
            url = urljoin(self.url, link)

            # 获取摘要
            summary = ""
            summary_elem = item.select_one(summary_selector)
            if summary_elem:
                summary = self._clean_text(summary_elem.get_text())

            return Article(
                url=url,
                title=title,
                source_id=self.source_id,
                source_name=self.source_name,
                summary=self._truncate_content(summary, 500),
            )

        except Exception as e:
            logger.error(f"[{self.source_id}] 解析项目失败: {e}")
            return None
