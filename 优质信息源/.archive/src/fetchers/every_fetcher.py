"""Every.to 专用抓取器"""
import subprocess
from bs4 import BeautifulSoup
from typing import Optional

from fetchers.base import BaseFetcher, Article
from utils.logger import logger


class EveryFetcher(BaseFetcher):
    """Every.to 专用抓取器"""

    def fetch(self) -> list[Article]:
        """抓取 Every.to 文章列表"""
        articles = []

        logger.info(f"[{self.source_id}] 正在抓取 Every.to: {self.url}")

        # 使用 curl 获取页面
        html = self._get_page_with_curl(self.url)
        if not html:
            html = self._get_page(self.url)

        if not html:
            return articles

        try:
            soup = BeautifulSoup(html, 'lxml')
            limit = self.config.get('limit', 15)
            seen_urls = set()

            # 查找所有文章链接
            for link in soup.select('a[href*="/p/"], a[href*="/chain-of-thought/"]'):
                href = link.get('href', '')
                if not href or href in seen_urls:
                    continue

                # 构建完整 URL
                if href.startswith('/'):
                    url = 'https://every.to' + href
                else:
                    url = href

                # 跳过非文章链接
                if '/p/' not in url and '/chain-of-thought/' not in url:
                    continue

                # 获取标题 - 在链接内找 h3/h2，或直接使用链接文本
                title = ''
                title_elem = link.select_one('h3, h2')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                else:
                    title = link.get_text(strip=True)

                # 跳过没有标题的链接
                if not title or len(title) < 5:
                    continue

                seen_urls.add(href)

                articles.append(Article(
                    url=url,
                    title=title,
                    source_id=self.source_id,
                    source_name=self.source_name,
                    summary='',
                ))

                if len(articles) >= limit:
                    break

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
