#!/usr/bin/env python3
"""情报收集系统主程序"""
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

        logger.info(f"[{source_id}] 新文章: {len(new_articles)}/{len(articles)}")
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

    # AI 处理
    if config.get('ai.enabled', True):
        logger.info(f"开始 AI 处理 {len(articles)} 篇文章...")
        articles = ai_processor.process_batch(articles)

    # 保存到数据库和 Obsidian
    saved_count = 0
    for article in articles:
        # 写入 Obsidian 文件
        file_path = obsidian_writer.write_article(article)

        # 保存到数据库
        article_data = article.to_dict()
        article_data['file_path'] = file_path
        article_data['processed_at'] = datetime.now().isoformat()

        if db.add_article(article_data):
            saved_count += 1

    return saved_count


def run_collection(source_ids: Optional[list[str]] = None):
    """运行收集任务"""
    start_time = time.time()
    logger.info("=" * 50)
    logger.info("开始情报收集...")
    logger.info("=" * 50)

    sources = config.sources
    if not sources:
        logger.error("未配置信息源，请检查 sources.yaml")
        notify_error("未配置信息源")
        return

    # 过滤指定的源
    if source_ids:
        sources = [s for s in sources if s.get('id') in source_ids]
        if not sources:
            logger.error(f"未找到指定的信息源: {source_ids}")
            return

    logger.info(f"准备抓取 {len(sources)} 个信息源")

    all_processed_articles = []
    delay = config.get('fetch.delay_between_sources', 2)

    for i, source_config in enumerate(sources):
        source_id = source_config.get('id', 'unknown')
        logger.info(f"[{i + 1}/{len(sources)}] 抓取 {source_id}...")

        new_articles = fetch_source(source_config)

        # 立即处理并保存当前源的新文章
        if new_articles:
            saved_count = process_and_save_articles(new_articles)
            if saved_count > 0:
                all_processed_articles.extend(new_articles)
                logger.info(f"[{source_id}] 已保存 {saved_count} 篇文章")

        # 源之间的延迟
        if i < len(sources) - 1 and delay > 0:
            time.sleep(delay)

    logger.info(f"抓取完成，共 {len(all_processed_articles)} 篇新文章")

    # 生成每日汇总和索引
    if all_processed_articles:
        # 生成每日汇总
        obsidian_writer.write_daily_summary(all_processed_articles)

        # 更新信息源索引
        obsidian_writer.write_source_index(sources)

    # 更新精华汇总（使用 dataview 动态查询，无需传入文章列表）
    obsidian_writer.update_favorites()

    # 统计信息
    elapsed = time.time() - start_time
    stats = db.get_stats()
    logger.info("=" * 50)
    logger.info(f"收集完成！耗时: {elapsed:.1f}秒")
    logger.info(f"今日新增: {len(all_processed_articles)} | 总计: {stats['total']} | 未读: {stats['unread']}")
    logger.info("=" * 50)

    # 发送通知
    if config.get('notification.enabled', True):
        notify_completion(len(all_processed_articles), len(sources))


def update_favorites():
    """更新精华汇总"""
    logger.info("更新精华汇总...")
    obsidian_writer.update_favorites()
    logger.info("精华汇总已更新（使用 dataview 动态显示精选文章）")


def show_stats():
    """显示统计信息"""
    stats = db.get_stats()
    print("\n📊 情报收集统计")
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
        logger.info("用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"运行错误: {e}", exc_info=True)
        notify_error(str(e)[:100])
        sys.exit(1)


if __name__ == '__main__':
    main()
