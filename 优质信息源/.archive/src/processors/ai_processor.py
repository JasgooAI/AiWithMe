"""AI 处理模块 - 使用 OpenAI 兼容接口"""
import json
import re
import time
from typing import Optional

from openai import OpenAI

from fetchers.base import Article
from utils.config import config
from utils.logger import logger


class AIProcessor:
    """使用 OpenAI 兼容 API 处理文章"""

    def __init__(self):
        api_key = config.api_key
        base_url = config.api_base_url

        if not api_key:
            logger.warning("未配置 API Key，AI 处理将被跳过")
            self.client = None
        else:
            self.client = OpenAI(
                base_url=base_url,
                api_key=api_key
            )
            logger.info(f"使用 API: {base_url}")

        self.model = config.api_model
        self.fallback_model = config.get('api.fallback_model', 'gemini-2.5-flash-lite')
        self.max_retries = 3
        self.retry_delay = 5

    def process_article(self, article: Article) -> Article:
        """处理单篇文章，主模型失败时自动回退到备用模型"""
        if not self.client:
            return article

        prompt = self._build_prompt(article)
        models_to_try = [self.model, self.fallback_model]

        for model in models_to_try:
            for attempt in range(self.max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}]
                    )

                    result = self._parse_response(response.choices[0].message.content)
                    if result:
                        article.title_zh = result.get('title_zh', article.title)
                        article.keywords = result.get('keywords', '')
                        article.ai_summary = result.get('summary', article.summary)
                        article.category = result.get('category', '其他')

                    logger.debug(f"AI 处理完成 ({model}): {article.title[:50]}")
                    return article

                except Exception as e:
                    error_msg = str(e)
                    # 429 容量不足或 503 服务不可用时，直接切换到备用模型
                    if '429' in error_msg or '503' in error_msg or 'RESOURCE_EXHAUSTED' in error_msg:
                        logger.warning(f"{model} 容量不足，切换到备用模型")
                        break  # 跳出重试循环，尝试下一个模型

                    logger.warning(f"AI 处理失败 ({model}, 尝试 {attempt + 1}/{self.max_retries}): {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)

        return article

    def process_batch(self, articles: list[Article], batch_size: int = 5) -> list[Article]:
        """批量处理文章"""
        if not self.client:
            return articles

        processed = []
        total = len(articles)

        for i, article in enumerate(articles):
            logger.info(f"处理文章 {i + 1}/{total}: {article.title[:40]}...")
            processed_article = self.process_article(article)
            processed.append(processed_article)

            # 批次间暂停，避免 API 限流
            if (i + 1) % batch_size == 0 and i + 1 < total:
                time.sleep(1)

        return processed

    def _build_prompt(self, article: Article) -> str:
        """构建 AI 处理提示"""
        content = article.content or article.summary or ""
        content = content[:1500]  # 限制长度

        return f"""分析文章，输出纯JSON（禁止```代码块）:

标题: {article.title}
来源: {article.source_name}
内容: {content}

JSON格式（字段顺序不可变）:
{{"title_zh":"中文标题","summary":"50字中文摘要","category":"分类","keywords":"关键词1,关键词2"}}

category: AI/技术/产品/商业/研究/工具/教程/新闻/其他"""

    def _parse_response(self, response_text: str) -> Optional[dict]:
        """解析 AI 响应"""
        text = response_text.strip()

        # 移除 markdown code block（各种格式）
        if '```' in text:
            text = re.sub(r'^```(?:json)?\s*\n?', '', text)
            text = re.sub(r'\n?```\s*$', '', text)
            text = text.strip()

        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 提取 JSON 对象
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # 处理截断的 JSON（没有闭合的 }）
        start = text.find('{')
        if start >= 0:
            json_str = text[start:]
            # 如果没有闭合的 }，尝试补全
            if json_str.count('{') > json_str.count('}'):
                # 尝试在最后一个完整字段后截断并闭合
                # 查找最后一个完整的 "key":"value" 模式
                match = re.search(r'^(.*"[^"]+"\s*:\s*"[^"]*")\s*,?\s*"[^"]*$', json_str, re.DOTALL)
                if match:
                    json_str = match.group(1) + '}'
                else:
                    # 直接在末尾加 "}
                    if json_str.endswith('...'):
                        json_str = json_str[:-3]
                    # 找到最后一个逗号前的完整字段
                    last_comma = json_str.rfind('","')
                    if last_comma > 0:
                        json_str = json_str[:last_comma] + '"}'
                    else:
                        json_str = json_str.rstrip('",. ') + '"}'

                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass

        # 最后尝试：用正则提取各字段
        try:
            result = {}
            title_match = re.search(r'"title_zh"\s*:\s*"([^"]*)"', text)
            if title_match:
                result['title_zh'] = title_match.group(1)
            keywords_match = re.search(r'"keywords"\s*:\s*"([^"]*)"', text)
            if keywords_match:
                result['keywords'] = keywords_match.group(1)
            summary_match = re.search(r'"summary"\s*:\s*"([^"]*)"', text)
            if summary_match:
                result['summary'] = summary_match.group(1)
            category_match = re.search(r'"category"\s*:\s*"([^"]*)"', text)
            if category_match:
                result['category'] = category_match.group(1)

            if result.get('title_zh'):  # 至少有标题才返回
                return result
        except:
            pass

        logger.warning(f"无法解析 AI 响应: {response_text[:150]}...")
        return None


# 全局 AI 处理器实例
ai_processor = AIProcessor()
