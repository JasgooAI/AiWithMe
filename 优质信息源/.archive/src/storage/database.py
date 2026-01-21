"""SQLite 数据库操作模块"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from utils.config import config
from utils.logger import logger


class Database:
    """数据库管理器"""

    def __init__(self):
        self.db_path = config.db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self) -> None:
        """确保数据库和表存在"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 文章表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT,
                    title_zh TEXT,
                    source_id TEXT NOT NULL,
                    source_name TEXT,
                    summary TEXT,
                    keywords TEXT,
                    category TEXT,
                    published_at TEXT,
                    fetched_at TEXT NOT NULL,
                    processed_at TEXT,
                    file_path TEXT,
                    is_read INTEGER DEFAULT 0,
                    rating INTEGER,
                    created_at TEXT NOT NULL
                )
            ''')

            # 抓取记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fetch_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    status TEXT,
                    article_count INTEGER DEFAULT 0,
                    error_message TEXT
                )
            ''')

            # 索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(fetched_at)')

            conn.commit()
            logger.debug("数据库初始化完成")

    @contextmanager
    def _get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def is_new_article(self, url: str) -> bool:
        """检查文章是否为新文章"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM articles WHERE url = ?', (url,))
            return cursor.fetchone() is None

    def add_article(self, article: dict) -> Optional[int]:
        """添加新文章"""
        if not self.is_new_article(article['url']):
            return None

        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO articles (
                    url, title, title_zh, source_id, source_name,
                    summary, keywords, category, published_at,
                    fetched_at, processed_at, file_path, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article['url'],
                article.get('title'),
                article.get('title_zh'),
                article['source_id'],
                article.get('source_name'),
                article.get('summary'),
                article.get('keywords'),
                article.get('category'),
                article.get('published_at'),
                now,
                article.get('processed_at'),
                article.get('file_path'),
                now
            ))
            conn.commit()
            logger.debug(f"添加文章: {article.get('title', article['url'])}")
            return cursor.lastrowid

    def update_article(self, url: str, updates: dict) -> bool:
        """更新文章信息"""
        if not updates:
            return False

        set_clause = ', '.join(f'{k} = ?' for k in updates.keys())
        values = list(updates.values()) + [url]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f'UPDATE articles SET {set_clause} WHERE url = ?',
                values
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_today_articles(self) -> list:
        """获取今日抓取的文章"""
        today = datetime.now().strftime('%Y-%m-%d')
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM articles
                WHERE DATE(fetched_at) = ?
                ORDER BY fetched_at DESC
            ''', (today,))
            return [dict(row) for row in cursor.fetchall()]

    def get_unprocessed_articles(self) -> list:
        """获取未处理的文章"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM articles
                WHERE processed_at IS NULL
                ORDER BY fetched_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]

    def log_fetch(self, source_id: str, status: str, article_count: int = 0, error: str = None) -> None:
        """记录抓取日志"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO fetch_logs (source_id, fetched_at, status, article_count, error_message)
                VALUES (?, ?, ?, ?, ?)
            ''', (source_id, datetime.now().isoformat(), status, article_count, error))
            conn.commit()

    def get_articles_by_rating(self, min_rating: int = 4) -> list:
        """获取指定评分以上的文章"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM articles
                WHERE rating >= ?
                ORDER BY rating DESC, fetched_at DESC
            ''', (min_rating,))
            return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM articles')
            total = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM articles WHERE is_read = 1')
            read = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM articles WHERE rating IS NOT NULL')
            rated = cursor.fetchone()[0]

            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('SELECT COUNT(*) FROM articles WHERE DATE(fetched_at) = ?', (today,))
            today_count = cursor.fetchone()[0]

            return {
                'total': total,
                'read': read,
                'unread': total - read,
                'rated': rated,
                'today': today_count
            }


# 全局数据库实例
db = Database()
