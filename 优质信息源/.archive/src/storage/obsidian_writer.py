"""Obsidian 文件生成模块"""
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from fetchers.base import Article
from utils.config import config
from utils.logger import logger


class ObsidianWriter:
    """Obsidian Markdown 文件生成器"""

    def __init__(self):
        self.paths = config.output_paths
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """确保输出目录存在"""
        for path in self.paths.values():
            path.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, title: str, max_length: int = 50) -> str:
        """清理文件名"""
        # 移除不允许的字符
        clean = re.sub(r'[<>:"/\\|?*\[\]#^]', '', title)
        # 移除多余空格
        clean = re.sub(r'\s+', ' ', clean).strip()
        # 截断
        if len(clean) > max_length:
            clean = clean[:max_length].strip()
        return clean or 'untitled'

    def _format_keywords_as_tags(self, keywords: str) -> str:
        """将关键词格式化为 Obsidian 标签"""
        if not keywords:
            return ""
        tags = [f"#{kw.strip().replace(' ', '-')}" for kw in keywords.split(',') if kw.strip()]
        return ' '.join(tags)

    def write_article(self, article: Article) -> Optional[str]:
        """写入单篇文章详情"""
        try:
            today = datetime.now()
            month_dir = self.paths['articles'] / today.strftime('%Y-%m')
            month_dir.mkdir(parents=True, exist_ok=True)

            # 生成文件名
            date_prefix = today.strftime('%Y%m%d')
            title_part = self._sanitize_filename(article.title_zh or article.title)
            filename = f"{date_prefix}-{title_part}.md"
            file_path = month_dir / filename

            # 生成内容
            title_zh = article.title_zh or article.title
            title_original = article.title if article.title_zh else ""
            tags = self._format_keywords_as_tags(article.keywords)
            summary = article.ai_summary or article.summary or ""

            content = f"""---
title: "{title_zh}"
title_original: "{title_original}"
url: {article.url}
source: {article.source_id}
source_name: {article.source_name}
category: {article.category or '其他'}
date: {today.strftime('%Y-%m-%d')}
---

# {title_zh}

**原标题**: {article.title}
**来源**: [[{article.source_id}]]
**链接**: [{article.url}]({article.url})
{f"**作者**: {article.author}" if article.author else ""}

## AI 摘要

> {summary}

## 关键词

{tags}

- [ ] 加入精选

## 阅读笔记


"""
            file_path.write_text(content, encoding='utf-8')
            logger.debug(f"写入文章: {file_path}")

            return str(file_path.relative_to(config.base_path))

        except Exception as e:
            logger.error(f"写入文章失败 {article.title}: {e}")
            return None

    def write_daily_summary(self, articles: list[Article], date: datetime = None) -> Optional[str]:
        """写入每日汇总（合并已有内容）"""
        if not articles:
            return None

        date = date or datetime.now()
        date_str = date.strftime('%Y-%m-%d')
        date_prefix = date.strftime('%Y%m%d')
        file_path = self.paths['daily_summary'] / f"{date_str}.md"

        try:
            # 读取已有文章链接（避免重复）
            existing_links = set()
            if file_path.exists():
                existing_content = file_path.read_text(encoding='utf-8')
                # 提取已有的文章链接 [[20260120-xxx|yyy]]
                existing_links = set(re.findall(r'\[\[(' + date_prefix + r'-[^\]|]+)', existing_content))
                logger.info(f"已有 {len(existing_links)} 篇文章在每日汇总中")

            # 过滤掉已存在的文章
            new_articles = []
            for article in articles:
                title_zh = article.title_zh or article.title
                safe_title = self._sanitize_filename(title_zh)
                link_name = f"{date_prefix}-{safe_title}"
                if link_name not in existing_links:
                    new_articles.append(article)

            if not new_articles and existing_links:
                logger.info("没有新文章需要添加到每日汇总")
                return str(file_path.relative_to(config.base_path))

            # 合并所有文章：从文章目录读取今天的所有文章
            all_articles = self._load_today_articles(date)
            # 添加新文章
            for article in new_articles:
                title_zh = article.title_zh or article.title
                safe_title = self._sanitize_filename(title_zh)
                link_name = f"{date_prefix}-{safe_title}"
                if link_name not in [a['link_name'] for a in all_articles]:
                    all_articles.append({
                        'link_name': link_name,
                        'title_zh': title_zh,
                        'title_original': article.title if article.title_zh and article.title_zh != article.title else "",
                        'category': article.category or '其他',
                        'source_id': article.source_id,
                        'tags': self._format_keywords_as_tags(article.keywords),
                        'summary': (article.ai_summary or article.summary or "")[:200],
                    })

            # 按分类分组
            by_category = {}
            for item in all_articles:
                category = item['category']
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(item)

            # 按来源统计
            by_source = {}
            for item in all_articles:
                source_id = item['source_id']
                if source_id not in by_source:
                    by_source[source_id] = 0
                by_source[source_id] += 1

            # 生成内容
            lines = [
                f"---",
                f"date: {date_str}",
                f"total_articles: {len(all_articles)}",
                f"---",
                f"",
                f"# 情报汇总 - {date_str}",
                f"",
                f"共收集 **{len(all_articles)}** 篇文章，来自 **{len(by_source)}** 个信息源",
                f"",
                f"## 信息源概览",
                f"",
                f"| 来源 | 数量 | 跳转 |",
                f"|------|------|------|",
            ]

            # 按数量排序输出来源
            for source_id, count in sorted(by_source.items(), key=lambda x: -x[1]):
                lines.append(f"| [[{source_id}]] | {count} | [→](#来源-{source_id}) |")

            lines.append("")

            # 按分类输出
            lines.append("---")
            lines.append("")
            lines.append("## 按分类浏览")
            lines.append("")

            category_order = ['AI', '技术', '产品', '商业', '研究', '工具', '教程', '新闻', '其他']
            for category in category_order:
                if category not in by_category:
                    continue

                lines.append(f"### {category}")
                lines.append("")

                for item in by_category[category]:
                    lines.append(f"#### [[{item['link_name']}|{item['title_zh']}]]")
                    if item['title_original']:
                        lines.append(f"*{item['title_original']}*")
                    lines.append(f"- {item['tags']}" if item['tags'] else "")
                    lines.append(f"- 来源: [[{item['source_id']}]]")
                    lines.append(f"> {item['summary']}")
                    lines.append("")

            # 按来源分组输出（用于跳转）
            lines.append("---")
            lines.append("")
            lines.append("## 按来源浏览")
            lines.append("")

            # 按来源分组文章
            source_articles = {}
            for item in all_articles:
                source_id = item['source_id']
                if source_id not in source_articles:
                    source_articles[source_id] = []
                source_articles[source_id].append(item)

            for source_id, items in sorted(source_articles.items(), key=lambda x: -len(x[1])):
                lines.append(f"### 来源-{source_id}")
                lines.append("")
                for item in items:
                    lines.append(f"- [[{item['link_name']}|{item['title_zh']}]]")
                lines.append("")

            content = '\n'.join(lines)
            file_path.write_text(content, encoding='utf-8')
            logger.info(f"写入每日汇总: {file_path} (共 {len(all_articles)} 篇)")

            return str(file_path.relative_to(config.base_path))

        except Exception as e:
            logger.error(f"写入每日汇总失败: {e}")
            return None

    def _load_today_articles(self, date: datetime) -> list[dict]:
        """从文章目录加载今天的所有文章"""
        articles = []
        date_prefix = date.strftime('%Y%m%d')
        month_dir = self.paths['articles'] / date.strftime('%Y-%m')

        if not month_dir.exists():
            return articles

        for file_path in month_dir.glob(f"{date_prefix}-*.md"):
            try:
                content = file_path.read_text(encoding='utf-8')
                # 解析 frontmatter
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        import yaml
                        meta = yaml.safe_load(parts[1])

                        link_name = file_path.stem
                        articles.append({
                            'link_name': link_name,
                            'title_zh': meta.get('title', link_name),
                            'title_original': meta.get('title_original', ''),
                            'category': meta.get('category', '其他'),
                            'source_id': meta.get('source', ''),
                            'tags': self._format_keywords_as_tags(','.join(meta.get('keywords', []) if isinstance(meta.get('keywords'), list) else [])),
                            'summary': self._extract_summary(parts[2]),
                        })
            except Exception as e:
                logger.debug(f"加载文章失败 {file_path}: {e}")

        return articles

    def _extract_summary(self, content: str) -> str:
        """从文章内容提取摘要"""
        # 查找 AI 摘要部分
        match = re.search(r'## AI 摘要\s*\n+>\s*(.+?)(?=\n\n|$)', content, re.DOTALL)
        if match:
            summary = match.group(1).strip()
            return summary[:200] if len(summary) > 200 else summary
        return ""

    def update_favorites(self, articles: list[dict] = None) -> Optional[str]:
        """更新精华汇总 - 使用 dataview 动态查询"""
        file_path = self.paths['favorites'] / "精华汇总.md"

        try:
            content = f"""---
updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
---

# 精华文章收藏

阅读后点选"加入精选"的优质文章会自动出现在这里。

## 按分类浏览

```dataview
TABLE WITHOUT ID
  link(file.link, title) as "标题",
  source_name as "来源",
  date as "日期"
FROM "优质信息源/文章"
FLATTEN file.tasks as T
WHERE T.text = "加入精选" AND T.completed
SORT date DESC
```

## 按来源统计

```dataview
TABLE WITHOUT ID
  source_name as "来源",
  length(rows) as "精选数量"
FROM "优质信息源/文章"
FLATTEN file.tasks as T
WHERE T.text = "加入精选" AND T.completed
GROUP BY source_name
SORT length(rows) DESC
```

## 精选笔记汇总

以下是所有精选文章的阅读笔记：

```dataviewjs
const pages = dv.pages('"优质信息源/文章"').where(p => {{
  return p.file.tasks.some(t => t.text.includes("加入精选") && t.completed);
}});

for (const page of pages) {{
  const content = await dv.io.load(page.file.path);
  const noteMatch = content.match(/## 阅读笔记\\n\\n([\\s\\S]*?)(?=\\n##|$)/);
  const note = noteMatch ? noteMatch[1].trim() : '';
  if (note) {{
    dv.header(4, page.title);
    dv.paragraph(`*${{page.source_name}} | ${{page.date}}*`);
    dv.paragraph(note);
    dv.paragraph('---');
  }}
}}
```
"""
            file_path.write_text(content, encoding='utf-8')
            logger.info(f"更新精华汇总: {file_path}")

            return str(file_path.relative_to(config.base_path))

        except Exception as e:
            logger.error(f"更新精华汇总失败: {e}")
            return None

    def write_source_index(self, sources: list[dict]) -> None:
        """生成信息源索引"""
        for source in sources:
            source_id = source.get('id', '')
            if not source_id:
                continue

            file_path = self.paths['sources_index'] / f"{source_id}.md"

            content = f"""---
id: {source_id}
name: {source.get('name', source_id)}
type: {source.get('type', 'unknown')}
url: {source.get('url', '')}
---

# {source.get('name', source_id)}

**类型**: {source.get('type', 'unknown')}
**URL**: {source.get('url', '')}
**描述**: {source.get('description', '')}

## 相关文章

```dataview
TABLE WITHOUT ID
  link(file.link, title) as "标题",
  title_original as "原标题",
  date as "日期"
FROM "优质信息源/文章"
WHERE source = "{source_id}"
SORT date DESC
LIMIT 20
```
"""
            file_path.write_text(content, encoding='utf-8')

        logger.info(f"生成 {len(sources)} 个信息源索引")


# 全局 Obsidian 写入器实例
obsidian_writer = ObsidianWriter()
