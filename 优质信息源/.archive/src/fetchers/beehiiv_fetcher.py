"""Beehiiv 平台抓取器"""
import re
import subprocess
from typing import Optional

from fetchers.base import BaseFetcher, Article
from utils.logger import logger


class BeehiivFetcher(BaseFetcher):
    """Beehiiv 平台专用抓取器，通过解析页面嵌入的 JSON 数据获取文章"""

    def fetch(self) -> list[Article]:
        """抓取 Beehiiv 网站文章"""
        articles = []

        logger.info(f"[{self.source_id}] 正在抓取 Beehiiv 网站: {self.url}")

        # 优先使用 curl 获取页面（更可靠）
        html = self._get_page_with_curl(self.url)
        if not html:
            # 备用：使用 requests
            html = self._get_page(self.url)

        if not html:
            return articles

        try:
            # 从 JSON 数据中提取文章
            posts = self._extract_posts_from_json(html)
            limit = self.config.get('limit', 15)

            for post in posts[:limit]:
                article = self._parse_post(post)
                if article:
                    articles.append(article)

            logger.info(f"[{self.source_id}] 抓取到 {len(articles)} 篇文章")

        except Exception as e:
            logger.error(f"[{self.source_id}] 抓取失败: {e}")

        return articles

    def _get_page_with_curl(self, url: str, timeout: int = 30) -> Optional[str]:
        """使用 curl 获取页面内容（绕过一些反爬虫限制）"""
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

    def _extract_posts_from_json(self, html: str) -> list[dict]:
        """从页面 HTML 中提取嵌入的 JSON 文章数据"""
        posts = []

        # 提取 web_title 和 parameterized_web_title 配对
        pattern = r'"web_title":"([^"]+)".*?"parameterized_web_title":"([^"]+)"'

        for match in re.finditer(pattern, html, re.DOTALL):
            title = match.group(1)
            slug = match.group(2)

            # 处理 Unicode 转义（安全方式）
            try:
                title = title.encode('utf-8').decode('unicode_escape')
            except:
                # 如果解码失败，使用原始字符串并手动处理常见转义
                title = title.replace('\\u0026', '&').replace('\\u003c', '<').replace('\\u003e', '>')

            posts.append({
                'title': title,
                'slug': slug,
            })

        # 去重（基于 slug）
        seen = set()
        unique_posts = []
        for post in posts:
            if post['slug'] not in seen:
                seen.add(post['slug'])
                unique_posts.append(post)

        return unique_posts

    def _parse_post(self, post: dict) -> Optional[Article]:
        """解析单篇文章"""
        try:
            title = post.get('title', '')
            slug = post.get('slug', '')

            if not title or not slug:
                return None

            # 构建完整 URL
            base_url = self.url.rstrip('/')
            url = f"{base_url}/p/{slug}"

            return Article(
                url=url,
                title=title,
                source_id=self.source_id,
                source_name=self.source_name,
                summary="",  # Beehiiv 页面通常没有摘要
            )

        except Exception as e:
            logger.error(f"[{self.source_id}] 解析文章失败: {e}")
            return None
