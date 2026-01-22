#!/usr/bin/env python3
"""情报收集系统主程序 - 带可视化进度"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.config import config
from utils.logger import logger
from utils.notifier import notify_completion, notify_error
from fetchers.base import Article
from fetchers.rss_fetcher import RSSFetcher
from fetchers.webpage_fetcher import WebpageFetcher
from fetchers.hackernews_fetcher import HackerNewsFetcher
from fetchers.huggingface_fetcher import HuggingFaceFetcher
from fetchers.beehiiv_fetcher import BeehiivFetcher
from fetchers.every_fetcher import EveryFetcher
from processors.ai_processor import ai_processor
from storage.database import db
from storage.obsidian_writer import obsidian_writer


# 抓取器映射
FETCHER_MAP = {
    'rss': RSSFetcher,
    'webpage': WebpageFetcher,
    'hackernews': HackerNewsFetcher,
    'huggingface': HuggingFaceFetcher,
    'beehiiv': BeehiivFetcher,
    'every': EveryFetcher,
}


class FetchProgress:
    """抓取进度显示"""

    def __init__(self, total_sources: int):
        self.total_sources = total_sources
        self.current_source = 0
        self.start_time = time.time()
        self.source_stats = {}  # {source_id: {"new": x, "total": y}}

    def start_source(self, source_id: str, source_name: str):
        """开始抓取某个源"""
        self.current_source += 1
        elapsed = time.time() - self.start_time

        # 预估剩余时间
        if self.current_source > 1:
            avg_time = elapsed / (self.current_source - 1)
            remaining = avg_time * (self.total_sources - self.current_source + 1)
            time_str = f"{int(remaining)}s" if remaining < 60 else f"{int(remaining//60)}m{int(remaining%60)}s"
        else:
            time_str = "计算中..."

        # 进度条
        bar_len = 20
        filled = int(bar_len * self.current_source / self.total_sources)
        bar = "█" * filled + "░" * (bar_len - filled)

        print(f"\r🔄 [{bar}] {self.current_source}/{self.total_sources} | 剩余:{time_str} | {source_name:<20}", end="", flush=True)

    def finish_source(self, source_id: str, new_count: int, total_count: int):
        """完成某个源的抓取"""
        self.source_stats[source_id] = {"new": new_count, "total": total_count}
        # 如果有新文章，显示一行
        if new_count > 0:
            print(f"\r✓ {source_id}: {new_count} 篇新文章" + " " * 40)

    def summary(self):
        """显示抓取汇总"""
        total_new = sum(s["new"] for s in self.source_stats.values())
        elapsed = time.time() - self.start_time
        print()
        print(f"📥 抓取完成: {self.total_sources} 个源, {total_new} 篇新文章, 耗时 {elapsed:.1f}s")


def get_fetcher(source_config: dict):
    """根据源类型获取对应的抓取器"""
    source_type = source_config.get('type', 'rss')
    fetcher_class = FETCHER_MAP.get(source_type, RSSFetcher)
    return fetcher_class(source_config)


def fetch_source(source_config: dict) -> list[Article]:
    """抓取单个信息源"""
    source_id = source_config.get('id', 'unknown')

    try:
        fetcher = get_fetcher(source_config)
        articles = fetcher.fetch()

        # 过滤已存在的文章
        new_articles = [a for a in articles if db.is_new_article(a.url)]

        logger.debug(f"[{source_id}] 新文章: {len(new_articles)}/{len(articles)}")
        db.log_fetch(source_id, 'success', len(new_articles))

        return new_articles

    except Exception as e:
        logger.error(f"[{source_id}] 抓取失败: {e}")
        db.log_fetch(source_id, 'error', error=str(e))
        return []


def process_and_save_articles(articles: list[Article]) -> int:
    """处理并保存文章"""
    if not articles:
        return 0

    # AI 处理（带进度显示）
    if config.get('ai.enabled', True):
        articles = ai_processor.process_batch(articles)

    # 保存到数据库和 Obsidian
    print(f"\n💾 保存文章...")
    saved_count = 0
    for i, article in enumerate(articles):
        # 写入 Obsidian 文件
        file_path = obsidian_writer.write_article(article)

        # 保存到数据库
        article_data = article.to_dict()
        article_data['file_path'] = file_path
        article_data['processed_at'] = datetime.now().isoformat()

        if db.add_article(article_data):
            saved_count += 1

        # 显示保存进度
        print(f"\r💾 保存进度: {i+1}/{len(articles)}", end="", flush=True)

    print(f"\r💾 已保存 {saved_count} 篇文章" + " " * 20)
    return saved_count


def run_collection(source_ids: Optional[list[str]] = None):
    """运行收集任务"""
    start_time = time.time()

    print()
    print("=" * 60)
    print(f"🚀 情报收集系统启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    sources = config.sources
    if not sources:
        print("❌ 未配置信息源，请检查 sources.yaml")
        notify_error("未配置信息源")
        return

    # 过滤指定的源
    if source_ids:
        sources = [s for s in sources if s.get('id') in source_ids]
        if not sources:
            print(f"❌ 未找到指定的信息源: {source_ids}")
            return

    print(f"📡 准备抓取 {len(sources)} 个信息源")
    print()

    # 阶段1: 抓取
    print("【阶段 1/3】抓取文章")
    print("-" * 40)

    progress = FetchProgress(len(sources))
    all_new_articles = []
    delay = config.get('fetch.delay_between_sources', 2)

    for i, source_config in enumerate(sources):
        source_id = source_config.get('id', 'unknown')
        source_name = source_config.get('name', source_id)

        progress.start_source(source_id, source_name)

        new_articles = fetch_source(source_config)
        progress.finish_source(source_id, len(new_articles), len(new_articles))

        all_new_articles.extend(new_articles)

        # 源之间的延迟
        if i < len(sources) - 1 and delay > 0:
            time.sleep(delay)

    progress.summary()

    if not all_new_articles:
        print("\n📭 没有新文章")
        elapsed = time.time() - start_time
        print(f"\n✅ 完成，耗时 {elapsed:.1f}s")
        return

    # 阶段2: AI处理和保存
    print()
    print("【阶段 2/3】AI 处理 & 保存")
    print("-" * 40)

    saved_count = process_and_save_articles(all_new_articles)

    # 阶段3: 生成汇总
    print()
    print("【阶段 3/3】生成汇总")
    print("-" * 40)

    if saved_count > 0:
        print("📊 生成每日汇总...")
        obsidian_writer.write_daily_summary(all_new_articles)

        print("📚 更新信息源索引...")
        obsidian_writer.write_source_index(sources)

    print("⭐ 更新精华汇总...")
    obsidian_writer.update_favorites()

    # 统计信息
    elapsed = time.time() - start_time
    stats = db.get_stats()

    print()
    print("=" * 60)
    print(f"✅ 收集完成！")
    print(f"   新增: {saved_count} 篇 | 总计: {stats['total']} 篇 | 耗时: {elapsed:.1f}s")
    print("=" * 60)

    # 发送通知
    if config.get('notification.enabled', True):
        notify_completion(saved_count, len(sources))


def update_favorites():
    """更新精华汇总"""
    print("⭐ 更新精华汇总...")
    obsidian_writer.update_favorites()
    print("✅ 精华汇总已更新")


def show_stats():
    """显示统计信息"""
    stats = db.get_stats()
    print()
    print("📊 情报收集统计")
    print("=" * 40)
    print(f"总文章数: {stats['total']}")
    print(f"已读: {stats['read']}")
    print(f"未读: {stats['unread']}")
    print(f"已评分: {stats['rated']}")
    print(f"今日新增: {stats['today']}")
    print("=" * 40)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='情报收集系统')
    parser.add_argument('--sources', '-s', nargs='+', help='指定要抓取的信息源 ID')
    parser.add_argument('--favorites', '-f', action='store_true', help='更新精华汇总')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    parser.add_argument('--debug', '-d', action='store_true', help='调试模式')

    args = parser.parse_args()

    # 调试模式
    if args.debug:
        import logging
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)

    try:
        if args.stats:
            show_stats()
        elif args.favorites:
            update_favorites()
        else:
            run_collection(args.sources)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"运行错误: {e}", exc_info=True)
        print(f"\n❌ 错误: {e}")
        notify_error(str(e)[:100])
        sys.exit(1)


if __name__ == '__main__':
    main()
