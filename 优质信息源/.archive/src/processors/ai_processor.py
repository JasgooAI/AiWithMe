"""AI 处理模块 - 支持多 API 提供商自动切换"""
import json
import re
import sys
import time
from dataclasses import dataclass
from typing import Optional, Callable

from openai import OpenAI

from fetchers.base import Article
from utils.config import config
from utils.logger import logger


@dataclass
class APIProvider:
    """API 提供商配置"""
    name: str
    base_url: str
    api_key: str
    model: str
    is_available: bool = True
    cooldown_until: float = 0  # 限流冷却时间戳


class ProgressReporter:
    """进度报告器"""

    def __init__(self, total: int, callback: Optional[Callable] = None):
        self.total = total
        self.current = 0
        self.start_time = time.time()
        self.callback = callback
        self.last_article = ""
        self.current_provider = ""
        self.errors = []

    def update(self, article_title: str, provider: str = "", status: str = "processing"):
        """更新进度"""
        self.current += 1
        self.last_article = article_title[:40]
        self.current_provider = provider
        if self.callback:
            self.callback(self.get_progress_info())
        else:
            self._print_progress(status)

    def add_error(self, msg: str):
        """记录错误"""
        self.errors.append(msg)

    def get_progress_info(self) -> dict:
        """获取进度信息"""
        elapsed = time.time() - self.start_time
        if self.current > 0:
            avg_time = elapsed / self.current
            remaining = (self.total - self.current) * avg_time
        else:
            remaining = 0

        return {
            "current": self.current,
            "total": self.total,
            "percent": (self.current / self.total * 100) if self.total > 0 else 0,
            "elapsed": elapsed,
            "remaining": remaining,
            "article": self.last_article,
            "provider": self.current_provider,
            "errors": len(self.errors),
        }

    def _print_progress(self, status: str = "processing"):
        """打印进度条"""
        info = self.get_progress_info()
        bar_len = 25
        filled = int(bar_len * info["current"] / info["total"]) if info["total"] > 0 else 0
        bar = "█" * filled + "░" * (bar_len - filled)

        # 格式化剩余时间
        remaining = info["remaining"]
        if remaining > 60:
            time_str = f"{int(remaining // 60)}m{int(remaining % 60)}s"
        else:
            time_str = f"{int(remaining)}s"

        # 状态符号
        status_icon = "⏳" if status == "processing" else ("✓" if status == "done" else "✗")

        line = f"\r{status_icon} [{bar}] {info['current']}/{info['total']} | 剩余:{time_str} | {info['provider']} | {info['article']}"
        # 清除行尾
        print(f"{line:<100}", end="", flush=True)

    def finish(self):
        """完成处理"""
        elapsed = time.time() - self.start_time
        print()  # 换行
        print(f"✅ AI 处理完成: {self.current}/{self.total} 篇, 耗时 {elapsed:.1f}s, 错误 {len(self.errors)} 个")


class AIProcessor:
    """支持多 API 提供商的 AI 处理器"""

    def __init__(self):
        self.providers: list[APIProvider] = []
        self.clients: dict[str, OpenAI] = {}
        self.max_retries = 3
        self.retry_delay = 2
        self.cooldown_period = 300  # 限流后冷却5分钟

        self._init_providers()

    def _init_providers(self):
        """初始化 API 提供商列表"""
        # 主 API（从配置文件）
        primary_key = config.api_key
        primary_url = config.api_base_url
        primary_model = config.api_model

        if primary_key and primary_url:
            self.providers.append(APIProvider(
                name="智谱AI",
                base_url=primary_url,
                api_key=primary_key,
                model=primary_model
            ))

        # 备用 API 列表（从配置文件）
        backup_apis = config.get("api.backup_providers", [])
        for api in backup_apis:
            if api.get("api_key") and api.get("base_url"):
                self.providers.append(APIProvider(
                    name=api.get("name", "备用API"),
                    base_url=api["base_url"],
                    api_key=api["api_key"],
                    model=api.get("model", "gpt-3.5-turbo")
                ))

        # 初始化客户端
        for provider in self.providers:
            try:
                self.clients[provider.name] = OpenAI(
                    base_url=provider.base_url,
                    api_key=provider.api_key
                )
                logger.info(f"已配置 API: {provider.name} ({provider.model})")
            except Exception as e:
                logger.warning(f"初始化 {provider.name} 失败: {e}")
                provider.is_available = False

        if not self.providers:
            logger.warning("未配置任何 API，AI 处理将被跳过")

    def _get_available_provider(self) -> Optional[tuple[APIProvider, OpenAI]]:
        """获取一个可用的 API 提供商"""
        current_time = time.time()

        for provider in self.providers:
            # 检查是否在冷却期
            if provider.cooldown_until > current_time:
                remaining = int(provider.cooldown_until - current_time)
                logger.debug(f"{provider.name} 冷却中，剩余 {remaining}s")
                continue

            if provider.is_available and provider.name in self.clients:
                return provider, self.clients[provider.name]

        # 所有提供商都不可用，找冷却时间最短的
        available_providers = [p for p in self.providers if p.name in self.clients]
        if available_providers:
            soonest = min(available_providers, key=lambda p: p.cooldown_until)
            wait_time = max(0, soonest.cooldown_until - current_time)
            if wait_time > 0:
                logger.info(f"所有 API 限流中，等待 {int(wait_time)}s...")
                time.sleep(min(wait_time, 60))  # 最多等60秒
            soonest.cooldown_until = 0  # 重置冷却
            return soonest, self.clients[soonest.name]

        return None, None

    def _mark_rate_limited(self, provider: APIProvider):
        """标记提供商被限流"""
        provider.cooldown_until = time.time() + self.cooldown_period
        logger.warning(f"{provider.name} 限流，冷却 {self.cooldown_period}s")

    def process_article(self, article: Article, progress: Optional[ProgressReporter] = None) -> Article:
        """处理单篇文章"""
        provider, client = self._get_available_provider()
        if not client:
            if progress:
                progress.add_error("无可用API")
            return article

        prompt = self._build_prompt(article)

        for attempt in range(self.max_retries):
            try:
                response = client.chat.completions.create(
                    model=provider.model,
                    messages=[{"role": "user", "content": prompt}]
                )

                result = self._parse_response(response.choices[0].message.content)
                if result:
                    article.title_zh = result.get("title_zh", article.title)
                    article.keywords = result.get("keywords", "")
                    article.ai_summary = result.get("summary", article.summary)
                    article.category = result.get("category", "其他")

                return article

            except Exception as e:
                error_msg = str(e)

                # 429 限流 - 切换提供商
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "rate" in error_msg.lower():
                    self._mark_rate_limited(provider)
                    # 尝试获取另一个提供商
                    provider, client = self._get_available_provider()
                    if not client:
                        if progress:
                            progress.add_error(f"所有API限流")
                        return article
                    continue

                # 其他错误 - 重试
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    if progress:
                        progress.add_error(f"{provider.name}: {error_msg[:50]}")
                    logger.warning(f"AI处理失败: {error_msg[:100]}")

        return article

    def process_batch(self, articles: list[Article], progress_callback: Optional[Callable] = None) -> list[Article]:
        """批量处理文章"""
        if not self.providers:
            return articles

        total = len(articles)
        progress = ProgressReporter(total, progress_callback)

        print(f"\n{'='*60}")
        print(f"🤖 AI 处理: {total} 篇文章")
        print(f"📡 可用 API: {', '.join(p.name for p in self.providers if p.is_available)}")
        print(f"{'='*60}\n")

        processed = []
        for i, article in enumerate(articles):
            provider, _ = self._get_available_provider()
            provider_name = provider.name if provider else "无"

            progress.update(article.title, provider_name, "processing")

            processed_article = self.process_article(article, progress)
            processed.append(processed_article)

            # 请求间隔
            if i + 1 < total:
                time.sleep(0.5)

        progress.finish()
        return processed

    def _build_prompt(self, article: Article) -> str:
        """构建 AI 处理提示"""
        content = article.content or article.summary or ""
        content = content[:1500]

        return f"""分析文章，输出纯JSON（禁止```代码块）:

标题: {article.title}
来源: {article.source_name}
内容: {content}

JSON格式（字段顺序不可变）:
{{"title_zh":"中文标题(英文则翻译,中文保持原样)","summary":"50字中文摘要","category":"分类","keywords":"关键词1,关键词2,关键词3"}}

category: AI/技术/产品/商业/研究/工具/教程/新闻/其他"""

    def _parse_response(self, response_text: str) -> Optional[dict]:
        """解析 AI 响应"""
        text = response_text.strip()

        # 移除 markdown code block
        if "```" in text:
            text = re.sub(r"^```(?:json)?\s*\n?", "", text)
            text = re.sub(r"\n?```\s*$", "", text)
            text = text.strip()

        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 提取 JSON 对象
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

        # 用正则提取各字段
        try:
            result = {}
            for field in ["title_zh", "keywords", "summary", "category"]:
                match = re.search(rf'"{field}"\s*:\s*"([^"]*)"', text)
                if match:
                    result[field] = match.group(1)
            if result.get("title_zh"):
                return result
        except:
            pass

        logger.warning(f"无法解析 AI 响应: {response_text[:100]}...")
        return None


# 全局 AI 处理器实例
ai_processor = AIProcessor()
